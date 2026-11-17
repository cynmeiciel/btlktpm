from fastapi.testclient import TestClient

from tests.fakes import (
    FakeHealthProbe,
    InMemoryAttendanceReader,
    InMemoryAttendanceStore,
)
from tmc_attendance.adapters.inbound.http.app import create_app
from tmc_attendance.adapters.inbound.http.dependencies import ApiDependencies
from tmc_attendance.application.history import GetAttendanceHistoryUseCase

ACTOR_ID = "00000000-0000-0000-0000-000000000010"
EMPLOYEE_REF = "00000000-0000-0000-0000-000000000001"
OTHER_EMPLOYEE_REF = "00000000-0000-0000-0000-000000000002"


def _client() -> TestClient:
    store = InMemoryAttendanceStore()
    deps = ApiDependencies(
        health=FakeHealthProbe(),
        history=GetAttendanceHistoryUseCase(InMemoryAttendanceReader(store)),
    )
    return TestClient(create_app(deps))


def _params() -> dict[str, str]:
    return {
        "from": "2026-11-03T00:00:00Z",
        "to": "2026-11-04T00:00:00Z",
    }


def test_history_requires_actor_headers() -> None:
    response = _client().get(
        f"/v1/employees/{EMPLOYEE_REF}/attendance-events",
        params=_params(),
    )

    assert response.status_code == 401


def test_employee_cannot_read_another_employees_history() -> None:
    response = _client().get(
        f"/v1/employees/{OTHER_EMPLOYEE_REF}/attendance-events",
        params=_params(),
        headers={
            "X-Actor-Id": ACTOR_ID,
            "X-Actor-Employee-Ref": EMPLOYEE_REF,
            "X-Actor-Roles": "EMPLOYEE",
        },
    )

    assert response.status_code == 403


def test_hr_can_read_another_employees_history() -> None:
    response = _client().get(
        f"/v1/employees/{OTHER_EMPLOYEE_REF}/attendance-events",
        params=_params(),
        headers={
            "X-Actor-Id": ACTOR_ID,
            "X-Actor-Roles": "HR",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"items": [], "hasMore": False}


def test_history_rejects_ranges_over_62_days() -> None:
    response = _client().get(
        f"/v1/employees/{EMPLOYEE_REF}/attendance-events",
        params={
            "from": "2026-11-03T00:00:00Z",
            "to": "2027-01-05T00:00:00Z",
        },
        headers={
            "X-Actor-Id": ACTOR_ID,
            "X-Actor-Employee-Ref": EMPLOYEE_REF,
            "X-Actor-Roles": "EMPLOYEE",
        },
    )

    assert response.status_code == 422


def test_missing_actor_is_401_even_when_query_is_invalid() -> None:
    response = _client().get(
        f"/v1/employees/{EMPLOYEE_REF}/attendance-events",
        params={"from": "not-a-date"},
    )

    assert response.status_code == 401


def test_history_is_503_when_use_case_is_not_wired() -> None:
    client = TestClient(create_app(ApiDependencies(health=FakeHealthProbe())))

    response = client.get(
        f"/v1/employees/{EMPLOYEE_REF}/attendance-events",
        params=_params(),
        headers={"X-Actor-Id": ACTOR_ID, "X-Actor-Roles": "HR"},
    )

    assert response.status_code == 503
