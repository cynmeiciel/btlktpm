"""Tests for station identifier validation."""

import pytest

from tmc_attendance.domain.errors import InvalidEvent
from tmc_attendance.domain.values import parse_station_id


@pytest.mark.parametrize(
    "value",
    [
        "BD-G01-IN",
        "LA_G02_OUT",
        "a",
        "A" * 64,
    ],
)
def test_valid_station_id_is_preserved(value: str) -> None:
    assert parse_station_id(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "",
        "A" * 65,
        "BD G01",
        "BD/G01",
        "BD.G01",
        " BD-G01-IN",
        "BD-G01-IN\n",
        "TRẠM-01",
    ],
)
def test_invalid_station_id_is_rejected(value: str) -> None:
    with pytest.raises(InvalidEvent) as exc_info:
        parse_station_id(value)

    assert exc_info.value.field == "stationId"
    assert exc_info.value.message
