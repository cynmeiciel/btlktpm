"""Tests for application command and station factories."""

from tests.factories import (
    SAMPLE_STATION_ID,
    event_fields,
    make_command,
    make_station,
)
from tmc_attendance.domain.model import Direction, EvidenceLevel


def test_command_contains_typed_event_data() -> None:
    fields = event_fields()

    command = make_command()

    assert command.event_id == fields["event_id"]
    assert command.station_id == SAMPLE_STATION_ID
    assert command.direction is Direction.IN
    assert command.evidence_level is EvidenceLevel.CONTROLLER_CONFIRMED
    assert command.occurred_at == fields["occurred_at"]


def test_command_preserves_values_for_use_case_validation() -> None:
    command = make_command(
        schema_version=2,
        local_sequence=-1,
    )

    assert command.schema_version == 2
    assert command.local_sequence == -1


def test_station_factory_uses_default_identifier() -> None:
    station = make_station()

    assert station.station_id == SAMPLE_STATION_ID


def test_station_factory_accepts_another_identifier() -> None:
    station = make_station("LA-G02-OUT")

    assert station.station_id == "LA-G02-OUT"
