import hashlib

from fastapi.testclient import TestClient

from tests.factories import SAMPLE_STATION_ID, SAMPLE_STATION_TOKEN, event_payload
from tests.fakes import FakeHealthProbe
from tmc_attendance.adapters.inbound.http.app import create_app
from tmc_attendance.adapters.inbound.http.dependencies import ApiDependencies
from tmc_attendance.adapters.outbound.station_auth import StaticTokenStationAuthenticator
from tmc_attendance.application.dto import (
    AuthenticatedStation,
    IngestEventCommand,
    IngestResult,
    IngestStatus,
)
from tmc_attendance.application.ingest_batch import IngestAttendanceBatchUseCase


class _AcceptEvent:
    def execute(self, command: IngestEventCommand, station: AuthenticatedStation) -> IngestResult:
        return IngestResult(status=IngestStatus.ACCEPTED, event_id=command.event_id)


def _client(*, use_case: bool = True, max_batch_size: int = 2) -> TestClient:
    token_hash = hashlib.sha256(SAMPLE_STATION_TOKEN.encode("utf-8")).hexdigest()
    app_dependencies = ApiDependencies(
        health=FakeHealthProbe(),
        station_authenticator=StaticTokenStationAuthenticator({SAMPLE_STATION_ID: token_hash}),
        ingest_batch=IngestAttendanceBatchUseCase(_AcceptEvent()) if use_case else None,
        max_batch_size=max_batch_size,
    )
    return TestClient(create_app(app_dependencies))


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {SAMPLE_STATION_TOKEN}"}


def test_ingest_batch_returns_ordered_results_and_ignores_unknown_fields() -> None:
    valid_item = event_payload(unrecognizedItemField="ignored")
    invalid_item = event_payload(occurredAt="private-invalid-datetime")
    payload = {
        "stationId": SAMPLE_STATION_ID,
        "events": [valid_item, invalid_item],
        "unrecognizedEnvelopeField": "ignored",
    }

    response = _client().post(
        "/v1/attendance-event-batches",
        headers=_headers(),
        json=payload,
    )

    assert response.status_code == 200
    assert response.json() == {
        "results": [
            {
                "index": 0,
                "eventId": "0b9f6c1e-6a52-4b7e-9a51-2f1b8d0c3a11",
                "status": "ACCEPTED",
            },
            {
                "index": 1,
                "eventId": "0b9f6c1e-6a52-4b7e-9a51-2f1b8d0c3a11",
                "status": "REJECTED",
                "reason": "INVALID_FORMAT",
                "errors": [{"field": "occurredAt", "message": "Input should be a valid datetime"}],
            },
        ],
        "summary": {"accepted": 1, "duplicate": 0, "conflict": 0, "rejected": 1},
    }
    assert "private-invalid-datetime" not in response.text


def test_ingest_batch_requires_station_authentication() -> None:
    response = _client().post(
        "/v1/attendance-event-batches",
        json={"stationId": SAMPLE_STATION_ID, "events": [event_payload()]},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_ingest_batch_rejects_station_mismatch() -> None:
    response = _client().post(
        "/v1/attendance-event-batches",
        headers=_headers(),
        json={"stationId": "BD-G02-IN", "events": [event_payload()]},
    )

    assert response.status_code == 403


def test_ingest_batch_rejects_empty_and_oversized_envelopes() -> None:
    client = _client()
    empty_response = client.post(
        "/v1/attendance-event-batches",
        headers=_headers(),
        json={"stationId": SAMPLE_STATION_ID, "events": []},
    )
    oversized_response = client.post(
        "/v1/attendance-event-batches",
        headers=_headers(),
        json={
            "stationId": SAMPLE_STATION_ID,
            "events": [event_payload(), event_payload(), event_payload()],
        },
    )

    assert empty_response.status_code == 422
    assert oversized_response.status_code == 422
    assert oversized_response.json() == {
        "detail": "Validation failed",
        "errors": [
            {
                "field": "events",
                "message": "List should have at most 2 items",
            }
        ],
    }


def test_ingest_batch_accepts_500_events_and_rejects_501() -> None:
    client = _client(max_batch_size=500)
    headers = _headers()
    accepted_response = client.post(
        "/v1/attendance-event-batches",
        headers=headers,
        json={
            "stationId": SAMPLE_STATION_ID,
            "events": [event_payload() for _ in range(500)],
        },
    )
    oversized_response = client.post(
        "/v1/attendance-event-batches",
        headers=headers,
        json={
            "stationId": SAMPLE_STATION_ID,
            "events": [event_payload() for _ in range(501)],
        },
    )

    assert accepted_response.status_code == 200
    assert accepted_response.json()["summary"]["accepted"] == 500
    assert len(accepted_response.json()["results"]) == 500
    assert oversized_response.status_code == 422


def test_ingest_batch_is_unavailable_without_application_use_case() -> None:
    response = _client(use_case=False).post(
        "/v1/attendance-event-batches",
        headers=_headers(),
        json={"stationId": SAMPLE_STATION_ID, "events": [event_payload()]},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Service unavailable"}
