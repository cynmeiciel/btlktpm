"""Ports: the interfaces the application layer needs from the outside world.

Adapters in ``tmc_attendance.adapters`` implement these explicitly. The full list is
specified in docs/01-kien-truc-s3.md §3; ports are added here as tasks land (T2.1).
"""

from abc import ABC, abstractmethod


class HealthProbe(ABC):
    """Tells whether the service can currently serve requests (readiness)."""

    @abstractmethod
    def is_ready(self) -> bool:
        """Return ``True`` when dependencies are reachable; never raise, never hang."""
