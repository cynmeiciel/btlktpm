"""HTTP controller for attendance event batch ingestion."""

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from tmc_attendance.adapters.inbound.http.dependencies import (
    ApiDependencies,
    get_api_dependencies,
)
from tmc_attendance.adapters.inbound.http.errors import field_name, safe_validation_message
from tmc_attendance.adapters.inbound.http.schemas import BatchIn, EventIn
from tmc_attendance.adapters.inbound.http.security import authenticate_station
from tmc_attendance.application.dto import (
    BatchItemResult,
    BatchSummary,
    IngestEventCommand,
    IngestStatus,
    InvalidItem,
    ValidationIssue,
)
from tmc_attendance.domain.values import parse_station_id

logger = logging.getLogger(__name__)


class EventIngestController:
    """Translate the station batch HTTP contract to the application use case."""

    def build_router(self) -> APIRouter:
        router = APIRouter(prefix="/v1", tags=["attendance"])
        router.add_api_route(
            "/attendance-event-batches",
            self.ingest_batch,
            methods=["POST"],
            response_model=None,
            responses={
                401: {"description": "Invalid station credentials"},
                403: {"description": "Envelope station does not match the token"},
                422: {"description": "Invalid request envelope"},
                503: {"description": "Ingestion service unavailable"},
            },
        )
        return router

    def ingest_batch(
        self,
        payload: BatchIn,
        request: Request,
        deps: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    ) -> dict[str, Any] | JSONResponse:
        authenticator = deps.station_authenticator
        if authenticator is None:
            logger.error("Station authenticator is not configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unavailable",
            )

        station = authenticate_station(request, authenticator)
        if payload.station_id != station.station_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Envelope stationId does not match the authenticated station.",
            )

        if len(payload.events) > deps.max_batch_size:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content={
                    "detail": "Validation failed",
                    "errors": [
                        {
                            "field": "events",
                            "message": f"List should have at most {deps.max_batch_size} items",
                        }
                    ],
                },
            )

        if deps.ingest_batch is None:
            logger.error("Attendance batch use case is not configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service unavailable",
            )

        items = [_parse_item(index, item) for index, item in enumerate(payload.events)]
        result = deps.ingest_batch.execute(items, station)
        for item_result in result.results:
            if item_result.status is IngestStatus.CONFLICT:
                logger.warning(
                    "Attendance event conflict station_id=%s event_id=%s",
                    station.station_id,
                    item_result.event_id,
                )
        logger.info(
            "Processed attendance batch station_id=%s accepted=%d duplicate=%d "
            "conflict=%d rejected=%d",
            station.station_id,
            result.summary.accepted,
            result.summary.duplicate,
            result.summary.conflict,
            result.summary.rejected,
        )
        return _serialize_batch(result.results, result.summary)


def _parse_item(index: int, raw_item: dict[str, Any]) -> IngestEventCommand | InvalidItem:
    try:
        event = EventIn.model_validate(raw_item)
    except ValidationError as exc:
        issues = tuple(
            ValidationIssue(
                field=field_name(error["loc"]),
                message=safe_validation_message(error["type"]),
            )
            for error in exc.errors()
        )
        return InvalidItem(
            index=index,
            event_id=_parse_event_id(raw_item.get("eventId")),
            errors=issues,
        )

    return IngestEventCommand(
        event_id=event.event_id,
        attempt_id=event.attempt_id,
        employee_ref=event.employee_ref,
        station_id=parse_station_id(event.station_id),
        direction=event.direction,
        occurred_at=event.occurred_at,
        local_sequence=event.local_sequence,
        evidence_level=event.evidence_level,
        schema_version=event.schema_version,
    )


def _parse_event_id(value: object) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except ValueError:
        return None


def _serialize_batch(
    results: tuple[BatchItemResult, ...],
    summary: BatchSummary,
) -> dict[str, Any]:
    serialized_results: list[dict[str, Any]] = []
    for result in results:
        item: dict[str, Any] = {
            "index": result.index,
            "eventId": str(result.event_id) if result.event_id is not None else None,
            "status": result.status.value,
        }
        if result.status in {IngestStatus.CONFLICT, IngestStatus.REJECTED} and result.reason:
            item["reason"] = result.reason
        if result.status is IngestStatus.REJECTED and result.reason == "INVALID_FORMAT":
            item["errors"] = [
                {"field": issue.field, "message": issue.message} for issue in result.errors
            ]
        serialized_results.append(item)

    return {
        "results": serialized_results,
        "summary": {
            "accepted": summary.accepted,
            "duplicate": summary.duplicate,
            "conflict": summary.conflict,
            "rejected": summary.rejected,
        },
    }
