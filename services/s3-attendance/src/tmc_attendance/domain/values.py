"""Value types and validation for attendance events."""

import re
from typing import NewType

from tmc_attendance.domain.errors import InvalidEvent

StationId = NewType("StationId", str)
PayloadHash = NewType("PayloadHash", str)

SUPPORTED_SCHEMA_VERSIONS: frozenset[int] = frozenset({1})


def parse_station_id(value: str) -> StationId:
    """Validate and return a station identifier."""
    if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value) is None:
        raise InvalidEvent(
            field="stationId",
            message=(
                "Must contain 1 to 64 characters using only "
                "letters, digits, underscores, or hyphens."
            ),
        )

    return StationId(value)
