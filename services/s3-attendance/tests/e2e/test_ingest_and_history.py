"""End-to-end: HTTP API + real composition root + PostgreSQL (docs/05-testing-strategy.md §3, E2E).

The app is wired exactly like production (``wire_api_dependencies``) on the runtime role
``s3_attendance_app``; only the engine comes from the test fixture so it is disposed afterwards.
"""

import hashlib
from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from tests.factories import SAMPLE_STATION_ID, SAMPLE_STATION_TOKEN, event_payload
from tmc_attendance.adapters.inbound.http.app import create_app
from tmc_attendance.bootstrap.config import Settings
from tmc_attendance.bootstrap.container import wire_api_dependencies

BATCHES = "/v1/attendance-event-batches"
EMPLOYEE_REF = "9e8d7c6b-5a49-4382-a1b0-c9d8e7f6a5b4"
STATION_HEADERS = {"Authorization": f"Bearer {SAMPLE_STATION_TOKEN}"}


@pytest.fixture
def client(app_engine: Engine) -> Iterator[TestClient]:
    settings = Settings(
        database_url="postgresql+psycopg://unused",  # the engine below is used instead
        station_tokens={
            SAMPLE_STATION_ID: hashlib.sha256(SAMPLE_STATION_TOKEN.encode()).hexdigest()
        },
    )
    with TestClient(create_app(wire_api_dependencies(app_engine, settings))) as test_client:
        yield test_client


def _batch(count: int) -> dict[str, object]:
    events = [
        event_payload(eventId=str(UUID(int=n + 1)), localSequence=n, employeeRef=EMPLOYEE_REF)
        for n in range(count)
    ]
    return {"stationId": SAMPLE_STATION_ID, "events": events}


def _count(engine: Engine, table: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())  # noqa: S608


def test_batch_is_accepted_and_resend_is_duplicate(
    client: TestClient, owner_engine: Engine
) -> None:
    first = client.post(BATCHES, headers=STATION_HEADERS, json=_batch(10))
    second = client.post(BATCHES, headers=STATION_HEADERS, json=_batch(10))

    assert first.status_code == 200
    assert first.json()["summary"] == {"accepted": 10, "duplicate": 0, "conflict": 0, "rejected": 0}
    assert second.json()["summary"] == {
        "accepted": 0,
        "duplicate": 10,
        "conflict": 0,
        "rejected": 0,
    }
    assert _count(owner_engine, "attendance.attendance_event") == 10
    assert _count(owner_engine, "attendance.outbox") == 10


def test_changed_payload_is_recorded_as_conflict_without_overwriting(
    client: TestClient, owner_engine: Engine
) -> None:
    original = event_payload(direction="IN")
    changed = event_payload(direction="OUT")

    client.post(
        BATCHES,
        headers=STATION_HEADERS,
        json={"stationId": SAMPLE_STATION_ID, "events": [original]},
    )
    for _ in range(2):  # resent conflicting payload is stored once
        response = client.post(
            BATCHES,
            headers=STATION_HEADERS,
            json={"stationId": SAMPLE_STATION_ID, "events": [changed]},
        )
        assert response.json()["results"][0]["status"] == "CONFLICT"

    with owner_engine.connect() as connection:
        direction = connection.execute(
            text("SELECT direction FROM attendance.attendance_event")
        ).scalar_one()
    assert direction == "IN"
    assert _count(owner_engine, "attendance.event_conflict") == 1


def test_employee_reads_own_history_after_ingest(client: TestClient) -> None:
    client.post(BATCHES, headers=STATION_HEADERS, json=_batch(3))

    response = client.get(
        f"/v1/employees/{EMPLOYEE_REF}/attendance-events",
        params={"from": "2026-11-01T00:00:00Z", "to": "2026-11-30T00:00:00Z"},
        headers={
            "X-Actor-Id": "3f1e0000-0000-4000-8000-000000000001",
            "X-Actor-Employee-Ref": EMPLOYEE_REF,
            "X-Actor-Roles": "EMPLOYEE",
        },
    )

    assert response.status_code == 200
    assert [item["eventId"] for item in response.json()["items"]] == [
        str(UUID(int=n + 1)) for n in range(3)
    ]
    assert response.json()["hasMore"] is False


def test_s4_reader_sees_accepted_events_through_versioned_view(
    client: TestClient, reader_engine: Engine
) -> None:
    client.post(BATCHES, headers=STATION_HEADERS, json=_batch(2))

    assert _count(reader_engine, "attendance.v1_attendance_event") == 2
