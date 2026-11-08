"""Tests for attendance event invariants."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta

import pytest

from tests.factories import make_event
from tmc_attendance.domain.errors import InvalidEvent
from tmc_attendance.domain.model import Direction, EvidenceLevel


def test_valid_event_has_typed_fields() -> None:
    event = make_event()

    assert event.station_id == "BD-G01-IN"
    assert event.direction is Direction.IN
    assert event.evidence_level is EvidenceLevel.CONTROLLER_CONFIRMED
    assert event.schema_version == 1


def test_naive_timestamp_is_rejected() -> None:
    naive_time = datetime(2026, 11, 3, 7, 58, 12)  # noqa: DTZ001 - Invalid test input.

    with pytest.raises(InvalidEvent) as exc_info:
        make_event(occurred_at=naive_time)

    assert exc_info.value.field == "occurredAt"


def test_negative_sequence_is_rejected() -> None:
    with pytest.raises(InvalidEvent) as exc_info:
        make_event(local_sequence=-1)

    assert exc_info.value.field == "localSequence"


def test_zero_sequence_is_valid() -> None:
    event = make_event(local_sequence=0)

    assert event.local_sequence == 0


def test_invalid_station_is_rejected_by_entity() -> None:
    with pytest.raises(InvalidEvent) as exc_info:
        make_event(station_id="BAD STATION")

    assert exc_info.value.field == "stationId"


def test_unsupported_schema_has_specific_error_field() -> None:
    with pytest.raises(InvalidEvent) as exc_info:
        make_event(schema_version=2)

    assert exc_info.value.field == "schemaVersion"


def test_event_preserves_original_timezone_offset() -> None:
    event = make_event()

    assert event.occurred_at.utcoffset() == timedelta(hours=7)


def test_event_cannot_be_modified() -> None:
    event = make_event()

    with pytest.raises(FrozenInstanceError):
        event.local_sequence = 999  # type: ignore[misc]
