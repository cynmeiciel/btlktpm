"""What the HTTP adapter needs, declared by the adapter itself.

``bootstrap`` builds an ``ApiDependencies`` from real adapters; API tests build one from
fakes. The adapter never imports ``bootstrap`` (dependency rule, docs/00-tong-quan.md §7).
"""

from dataclasses import dataclass

from fastapi import Request

from tmc_attendance.application.history import GetAttendanceHistoryUseCase
from tmc_attendance.application.ingest_batch import IngestAttendanceBatchUseCase
from tmc_attendance.application.ports import HealthProbe, StationAuthenticator


@dataclass(frozen=True, slots=True)
class ApiDependencies:
    """Use cases and ports exposed to the routes. Grows as features land (T4.x)."""

    health: HealthProbe
    station_authenticator: StationAuthenticator | None = None
    ingest_batch: IngestAttendanceBatchUseCase | None = None
    max_batch_size: int = 500
    history: GetAttendanceHistoryUseCase | None = None


def get_api_dependencies(request: Request) -> ApiDependencies:
    """FastAPI dependency: the object passed to ``create_app``."""
    deps: ApiDependencies = request.app.state.api_dependencies
    return deps
