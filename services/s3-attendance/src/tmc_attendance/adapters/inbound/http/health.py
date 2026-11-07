"""Liveness and readiness routes (docs/03-api-contract.md §4)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from tmc_attendance.adapters.inbound.http.dependencies import (
    ApiDependencies,
    get_api_dependencies,
)

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def live() -> dict[str, str]:
    """The process is running. Never touches the database."""
    return {"status": "ok"}


@router.get("/ready", responses={503: {"description": "Dependencies are not reachable"}})
def ready(deps: Annotated[ApiDependencies, Depends(get_api_dependencies)]) -> JSONResponse:
    """The service can serve requests: the database answers."""
    if deps.health.is_ready():
        return JSONResponse({"status": "ready"})
    return JSONResponse({"status": "not_ready"}, status_code=503)
