"""HTTP route for an employee's attendance history (UC09, docs/03-api-contract.md §3)."""

import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from tmc_attendance.adapters.inbound.http.dependencies import (
    ApiDependencies,
    get_api_dependencies,
)
from tmc_attendance.adapters.inbound.http.security import read_actor
from tmc_attendance.application.dto import HistoryQuery
from tmc_attendance.application.errors import AccessDenied, InvalidQuery
from tmc_attendance.domain.access import ActorContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["attendance-history"])


def _utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


@router.get("/employees/{employeeRef}/attendance-events")
def get_attendance_history(
    actor: Annotated[ActorContext, Depends(read_actor)],
    employee_ref: Annotated[UUID, Path(alias="employeeRef")],
    occurred_from: Annotated[datetime, Query(alias="from")],
    occurred_to: Annotated[datetime, Query(alias="to")],
    deps: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    if deps.history is None:
        logger.error("Attendance history use case is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable",
        )

    query = HistoryQuery(
        employee_ref=employee_ref,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        limit=limit,
        offset=offset,
    )

    try:
        page = deps.history.execute(query, actor)
    except AccessDenied:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied") from None
    except InvalidQuery:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid history query",
        ) from None

    return {
        "items": [
            {
                "eventId": str(item.event_id),
                "stationId": item.station_id,
                "direction": item.direction.value,
                "occurredAt": _utc_iso(item.occurred_at),
                "receivedAt": _utc_iso(item.received_at),
                "evidenceLevel": item.evidence_level.value,
            }
            for item in page.items
        ],
        "hasMore": page.has_more,
    }
