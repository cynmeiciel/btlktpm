"""Interfaces required by application use cases."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Self
from uuid import UUID

from tmc_attendance.application.dto import (
    AuthenticatedStation,
    EventConflict,
    HistoryPage,
    OutboxMessage,
)
from tmc_attendance.domain.model import AttendanceEvent
from tmc_attendance.domain.values import PayloadHash


class Clock(ABC):
    """Provide timezone-aware UTC timestamps."""

    @abstractmethod
    def now(self) -> datetime:
        """Return the current time as an aware UTC datetime."""


class IdGenerator(ABC):
    """Generate identifiers for records created by S3."""

    @abstractmethod
    def new_id(self) -> UUID:
        """Return a new identifier for an outbox message or conflict."""


@dataclass(frozen=True, slots=True)
class Inserted:
    """Indicate that a new event was inserted into the transaction."""


@dataclass(frozen=True, slots=True)
class EventIdExists:
    """Expose the stored hash when an event identifier already exists."""

    existing_hash: PayloadHash


InsertOutcome = Inserted | EventIdExists


class AttendanceWriter(ABC):
    """Write attendance events and conflict evidence."""

    @abstractmethod
    def insert_if_absent(
        self,
        event: AttendanceEvent,
        payload_hash: PayloadHash,
        received_at: datetime,
    ) -> InsertOutcome:
        """Insert a new event or return its existing hash without overwriting."""

    @abstractmethod
    def record_conflict(self, conflict: EventConflict) -> None:
        """Persist conflict evidence within the current transaction."""


class OutboxPort(ABC):
    """Persist messages in the same transaction as business changes."""

    @abstractmethod
    def add(self, message: OutboxMessage) -> None:
        """Stage a message without committing the transaction."""


class UnitOfWork(ABC):
    """Coordinate atomic event, conflict, and outbox persistence."""

    attendance: AttendanceWriter
    outbox: OutboxPort

    def __enter__(self) -> Self:
        """Return the unit of work; adapters may override to open resources."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Discard pending changes without suppressing exceptions."""
        self.rollback()

    @abstractmethod
    def commit(self) -> None:
        """Persist all pending changes atomically or raise an exception."""

    @abstractmethod
    def rollback(self) -> None:
        """Discard pending changes; do nothing when none remain."""


UnitOfWorkFactory = Callable[[], UnitOfWork]


class AttendanceReader(ABC):
    """Read attendance history without granting write capabilities."""

    @abstractmethod
    def list_by_employee(
        self,
        employee_ref: UUID,
        occurred_from: datetime,
        occurred_to: datetime,
        limit: int,
        offset: int,
    ) -> HistoryPage:
        """Read the half-open time range, ordered by occurred_at and event_id."""


class StationAuthenticator(ABC):
    """Resolve a station identity from a device credential."""

    @abstractmethod
    def authenticate(self, bearer_token: str) -> AuthenticatedStation | None:
        """Return the authenticated station, or None for invalid credentials."""


class HealthProbe(ABC):
    """Report whether the service dependencies are available."""

    @abstractmethod
    def is_ready(self) -> bool:
        """Return readiness without raising exceptions or hanging."""
