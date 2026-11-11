"""Attendance event entities and their invariants."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from tmc_attendance.domain.errors import InvalidEvent
from tmc_attendance.domain.values import (
    SUPPORTED_SCHEMA_VERSIONS,
    StationId,
    parse_station_id,
)


class Direction(StrEnum):
    IN = "IN"
    OUT = "OUT"


class EvidenceLevel(StrEnum):
    CONTROLLER_CONFIRMED = "CONTROLLER_CONFIRMED"
    CONTROLLER_UNCONFIRMED = "CONTROLLER_UNCONFIRMED"
    GUARD_RECORDED = "GUARD_RECORDED"


@dataclass(frozen=True, slots=True)
class AttendanceEvent:
    """Represent an immutable attendance event received from a station."""

    event_id: UUID
    attempt_id: UUID
    employee_ref: UUID
    station_id: StationId
    direction: Direction
    occurred_at: datetime
    local_sequence: int
    evidence_level: EvidenceLevel
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise InvalidEvent(
                field="occurredAt",
                message="Must include a timezone offset.",
            )

        if self.local_sequence < 0:
            raise InvalidEvent(
                field="localSequence",
                message="Must be greater than or equal to zero.",
            )

        parse_station_id(self.station_id)

        if self.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise InvalidEvent(
                field="schemaVersion",
                message="Unsupported schema version.",
            )
