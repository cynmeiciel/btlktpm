from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from tests.fakes import (
    FakeHealthProbe,
    InMemoryAttendanceReader,
    InMemoryAttendanceStore,
)
from tmc_attendance.adapters.inbound.http.app import create_app
from tmc_attendance.adapters.inbound.http.dependencies import ApiDependencies
from tmc_attendance.application.history import GetAttendanceHistoryUseCase


def _client() -> TestClient:
    store = InMemoryAttendanceStore()
    history = GetAttendanceHistoryUseCase(InMemoryAttendanceReader(store))
    app = create_app(ApiDependencies(health=FakeHealthProbe(), history=history))

    @app.get("/test-validation")
    def validation_route(value: int) -> dict[str, int]:
        return {"value": value}

    @app.get("/test-database-error")
    def database_error_route() -> None:
        raise OperationalError(
            "SELECT secret",
            {"password": "do-not-return"},
            RuntimeError("database secret"),
        )

    return TestClient(app)


def test_validation_error_does_not_expose_input_values() -> None:
    response = _client().get("/test-validation", params={"value": "private-input"})

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Validation failed",
        "errors": [{"field": "value", "message": "Input should be a valid integer"}],
    }
    assert "private-input" not in response.text
    assert "input" not in response.text


def test_database_operational_error_returns_generic_503() -> None:
    response = _client().get("/test-database-error")

    assert response.status_code == 503
    assert response.json() == {"detail": "Service unavailable"}
    assert "secret" not in response.text
