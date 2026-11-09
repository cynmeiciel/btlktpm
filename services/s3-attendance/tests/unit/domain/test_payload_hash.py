"""Tests for the version-one canonical payload and hash contract."""

from datetime import UTC, timedelta
from uuid import UUID

import pytest

from tests.factories import make_event
from tmc_attendance.domain.dedup import (
    canonical_payload,
    compute_payload_hash,
)
from tmc_attendance.domain.model import Direction, EvidenceLevel


def test_canonical_payload_matches_version_one_contract() -> None:
    event = make_event()

    expected = (
        b'{"attemptId":"5a3c2e10-1d4f-4c8b-8f7e-0a9b1c2d3e4f",'
        b'"direction":"IN",'
        b'"employeeRef":"9e8d7c6b-5a49-4382-a1b0-c9d8e7f6a5b4",'
        b'"eventId":"0b9f6c1e-6a52-4b7e-9a51-2f1b8d0c3a11",'
        b'"evidenceLevel":"CONTROLLER_CONFIRMED",'
        b'"localSequence":1042,'
        b'"occurredAt":"2026-11-03T00:58:12.345000+00:00",'
        b'"schemaVersion":1,'
        b'"stationId":"BD-G01-IN"}'
    )

    assert canonical_payload(event) == expected


def test_payload_hash_matches_known_version_one_digest() -> None:
    event = make_event()

    assert compute_payload_hash(event) == (
        "d1254190be6142d291c2514b0d33d1fea71331c1c11aa2b3d4226e1da2eb400a"
    )


def test_equivalent_timezone_offsets_produce_same_payload_and_hash() -> None:
    local_event = make_event()
    utc_event = make_event(
        occurred_at=local_event.occurred_at.astimezone(UTC),
    )

    assert canonical_payload(local_event) == canonical_payload(utc_event)
    assert compute_payload_hash(local_event) == compute_payload_hash(utc_event)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("event_id", UUID(int=1)),
        ("attempt_id", UUID(int=2)),
        ("employee_ref", UUID(int=3)),
        ("station_id", "LA-G02-OUT"),
        ("direction", Direction.OUT),
        (
            "occurred_at",
            make_event().occurred_at + timedelta(microseconds=1),
        ),
        ("local_sequence", 1043),
        ("evidence_level", EvidenceLevel.GUARD_RECORDED),
    ],
)
def test_changed_event_field_changes_hash(field: str, value: object) -> None:
    original = make_event()
    changed = make_event(**{field: value})

    assert compute_payload_hash(original) != compute_payload_hash(changed)
