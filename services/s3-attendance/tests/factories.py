"""Valid test data with per-test overrides.

T0.5 provides the raw building blocks. Typed factories are added by the tasks that
introduce the types, on top of these dicts:

- ``make_event(**overrides) -> AttendanceEvent``      — T1.1, wraps ``event_fields``
- ``make_command(**overrides) -> IngestEventCommand`` — T2.1
- ``make_station(...) -> AuthenticatedStation``      — T2.1
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from tmc_attendance.application.dto import (
    AuthenticatedStation,
    IngestEventCommand,
)
from tmc_attendance.domain.model import (
    AttendanceEvent,
    Direction,
    EvidenceLevel,
)
from tmc_attendance.domain.values import StationId, parse_station_id

SAMPLE_STATION_ID = "BD-G01-IN"
SAMPLE_STATION_TOKEN = "dev-token-bd-g01-in"  # dev-only; its sha256 is in .env.example
ICT = timezone(timedelta(hours=7), "ICT")


def event_fields(**overrides: Any) -> dict[str, Any]:
    """Valid ``AttendanceEvent`` field values, keyed by the dataclass field names (02 §3).

    Enum fields are plain strings until T1.1 introduces ``Direction``/``EvidenceLevel``.
    """
    fields: dict[str, Any] = {
        "event_id": UUID("0b9f6c1e-6a52-4b7e-9a51-2f1b8d0c3a11"),
        "attempt_id": UUID("5a3c2e10-1d4f-4c8b-8f7e-0a9b1c2d3e4f"),
        "employee_ref": UUID("9e8d7c6b-5a49-4382-a1b0-c9d8e7f6a5b4"),
        "station_id": SAMPLE_STATION_ID,
        "direction": "IN",
        "occurred_at": datetime(2026, 11, 3, 7, 58, 12, 345000, tzinfo=ICT),
        "local_sequence": 1042,
        "evidence_level": "CONTROLLER_CONFIRMED",
        "schema_version": 1,
    }
    unknown = overrides.keys() - fields.keys()
    if unknown:
        raise TypeError(f"unknown event field(s): {sorted(unknown)}")
    fields.update(overrides)
    return fields


def event_payload(**overrides: Any) -> dict[str, Any]:
    """One item of ``events[]`` as the HTTP API receives it (camelCase JSON, 03 §2).

    Overrides use the camelCase API names and are applied after serialisation, so a test
    can inject malformed values (e.g. ``occurredAt="2026-11-03T07:58:12"``) or extra keys.
    """
    f = event_fields()
    payload: dict[str, Any] = {
        "eventId": str(f["event_id"]),
        "attemptId": str(f["attempt_id"]),
        "employeeRef": str(f["employee_ref"]),
        "stationId": f["station_id"],
        "direction": f["direction"],
        "occurredAt": f["occurred_at"].isoformat(timespec="milliseconds"),
        "localSequence": f["local_sequence"],
        "evidenceLevel": f["evidence_level"],
        "schemaVersion": f["schema_version"],
    }
    payload.update(overrides)
    return payload


def make_event(**overrides: Any) -> AttendanceEvent:
    """Build a typed event from valid defaults and optional overrides."""
    fields = event_fields(**overrides)

    fields["direction"] = Direction(fields["direction"])
    fields["evidence_level"] = EvidenceLevel(fields["evidence_level"])
    fields["station_id"] = StationId(fields["station_id"])

    return AttendanceEvent(**fields)


def make_command(**overrides: Any) -> IngestEventCommand:
    """Build an ingestion command without enforcing entity invariants."""
    fields = event_fields(**overrides)

    fields["direction"] = Direction(fields["direction"])
    fields["evidence_level"] = EvidenceLevel(fields["evidence_level"])
    fields["station_id"] = StationId(fields["station_id"])

    return IngestEventCommand(**fields)


def make_station(
    station_id: str = SAMPLE_STATION_ID,
) -> AuthenticatedStation:
    """Build an authenticated station with a valid identifier."""
    return AuthenticatedStation(station_id=parse_station_id(station_id))
