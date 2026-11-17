"""System clock adapter for the ``Clock`` port."""

from datetime import UTC, datetime

from tmc_attendance.application.ports import Clock


class SystemClock(Clock):
    """Read the host clock. The only place in ``src/`` that calls ``datetime.now``."""

    def now(self) -> datetime:
        return datetime.now(UTC)
