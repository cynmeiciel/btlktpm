from fastapi.testclient import TestClient

from tests.fakes import (
    FakeHealthProbe,
    InMemoryAttendanceReader,
    InMemoryAttendanceStore,
)
from tmc_attendance.adapters.inbound.http.app import create_app
from tmc_attendance.adapters.inbound.http.dependencies import ApiDependencies
from tmc_attendance.application.history import GetAttendanceHistoryUseCase


def _client(*, ready: bool) -> TestClient:
    store = InMemoryAttendanceStore()
    history = GetAttendanceHistoryUseCase(InMemoryAttendanceReader(store))
    deps = ApiDependencies(health=FakeHealthProbe(ready=ready), history=history)
    return TestClient(create_app(deps))


def test_live_is_ok_even_when_not_ready() -> None:
    response = _client(ready=False).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_when_probe_is_ready() -> None:
    response = _client(ready=True).get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_returns_503_when_probe_is_not_ready() -> None:
    response = _client(ready=False).get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
