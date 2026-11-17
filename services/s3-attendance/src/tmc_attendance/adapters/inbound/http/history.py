from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from tmc_attendance.adapters.inbound.http.dependencies import (
    ApiDependencies,
    get_api_dependencies,
)
from tmc_attendance.adapters.inbound.http.security import read_actor
from tmc_attendance.application.dto import HistoryQuery
from tmc_attendance.application.errors import AccessDenied, InvalidQuery

router = APIRouter(prefix="/v1", tags=["attendance-history"])


def _utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


@router.get("/employees/{employeeRef}/attendance-events")
def get_attendance_history(
    request: Request,
    employee_ref: Annotated[UUID, Path(alias="employeeRef")],
    occurred_from: Annotated[datetime, Query(alias="from")],
    occurred_to: Annotated[datetime, Query(alias="to")],
    deps: Annotated[ApiDependencies, Depends(get_api_dependencies)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, object]:
    actor = read_actor(request)
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
        raise HTTPException(status_code=403, detail="Access denied") from None
    except InvalidQuery:
        raise HTTPException(status_code=422, detail="Invalid history query") from None

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
