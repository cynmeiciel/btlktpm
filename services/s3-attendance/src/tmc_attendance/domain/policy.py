"""Ingestion statuses and event rejection reasons."""

from datetime import datetime, timedelta
from enum import StrEnum

from tmc_attendance.domain.model import AttendanceEvent


class IngestStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    REJECTED = "REJECTED"


class RejectionReason(StrEnum):
    INVALID_FORMAT = "INVALID_FORMAT"
    UNSUPPORTED_SCHEMA_VERSION = "UNSUPPORTED_SCHEMA_VERSION"
    CLOCK_SKEW = "CLOCK_SKEW"
    STATION_MISMATCH = "STATION_MISMATCH"


class EventValidationPolicy:
    """Reject events whose timestamps exceed the allowed future skew."""

    def __init__(self, max_future_skew: timedelta) -> None:
        self._max_future_skew = max_future_skew

    def check(
        self,
        event: AttendanceEvent,
        received_at: datetime,
    ) -> RejectionReason | None:
        """Return a rejection reason, or None when the event is acceptable."""
        if event.occurred_at > received_at + self._max_future_skew:
            return RejectionReason.CLOCK_SKEW

        return None
