"""In-memory implementations of application ports for tests."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from tmc_attendance.application.dto import (
    AttendanceEventView,
    AuthenticatedStation,
    EventConflict,
    HistoryPage,
    OutboxMessage,
)
from tmc_attendance.application.ports import (
    AttendanceReader,
    AttendanceWriter,
    Clock,
    EventIdExists,
    HealthProbe,
    IdGenerator,
    Inserted,
    InsertOutcome,
    OutboxPort,
    StationAuthenticator,
    UnitOfWork,
)
from tmc_attendance.domain.model import AttendanceEvent
from tmc_attendance.domain.values import PayloadHash


class FakeHealthProbe(HealthProbe):
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = ready

    def is_ready(self) -> bool:
        return self.ready


class FixedClock(Clock):
    """Provide a controllable UTC clock without reading system time."""

    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None or at.utcoffset() is None:
            raise ValueError("Clock time must include a timezone offset.")

        self._at = at.astimezone(UTC)

    def now(self) -> datetime:
        return self._at

    def advance(self, delta: timedelta) -> None:
        """Move the clock without waiting in real time."""
        self._at += delta


class SequentialIdGenerator(IdGenerator):
    """Generate a repeatable sequence of UUIDs for tests."""

    def __init__(self) -> None:
        self._next_value = 1

    def new_id(self) -> UUID:
        identifier = UUID(int=self._next_value)
        self._next_value += 1
        return identifier


@dataclass(frozen=True, slots=True)
class StoredAttendanceEvent:
    """Keep an event and its persistence metadata."""

    event: AttendanceEvent
    payload_hash: PayloadHash
    received_at: datetime


class InMemoryAttendanceStore:
    """Hold records for a committed store or a transaction buffer."""

    def __init__(self) -> None:
        self.events: dict[UUID, StoredAttendanceEvent] = {}
        self.conflicts: list[EventConflict] = []
        self.outbox: list[OutboxMessage] = []

    def count(self) -> int:
        return len(self.events)


class InMemoryAttendanceWriter(AttendanceWriter):
    """Stage event writes without modifying committed records."""

    def __init__(
        self,
        store: InMemoryAttendanceStore,
        pending: InMemoryAttendanceStore,
    ) -> None:
        self._store = store
        self._pending = pending

    def insert_if_absent(
        self,
        event: AttendanceEvent,
        payload_hash: PayloadHash,
        received_at: datetime,
    ) -> InsertOutcome:
        existing = self._pending.events.get(event.event_id)

        if existing is None:
            existing = self._store.events.get(event.event_id)

        if existing is not None:
            return EventIdExists(existing_hash=existing.payload_hash)

        self._pending.events[event.event_id] = StoredAttendanceEvent(
            event=event,
            payload_hash=payload_hash,
            received_at=received_at,
        )
        return Inserted()

    def record_conflict(self, conflict: EventConflict) -> None:
        self._pending.conflicts.append(conflict)


class InMemoryOutbox(OutboxPort):
    """Stage messages or simulate a persistence failure."""

    def __init__(
        self,
        pending: InMemoryAttendanceStore,
        *,
        fail_on_add: bool = False,
    ) -> None:
        self._pending = pending
        self._fail_on_add = fail_on_add

    def add(self, message: OutboxMessage) -> None:
        if self._fail_on_add:
            raise RuntimeError("Simulated outbox failure.")

        self._pending.outbox.append(message)


class InMemoryUnitOfWork(UnitOfWork):
    """Buffer writes and publish them only when commit succeeds."""

    def __init__(
        self,
        store: InMemoryAttendanceStore,
        *,
        fail_on_commit: bool = False,
        fail_on_outbox_add: bool = False,
    ) -> None:
        self._store = store
        self._pending = InMemoryAttendanceStore()
        self._fail_on_commit = fail_on_commit
        self._finished = False
        self.commits = 0
        self.rollbacks = 0

        self.attendance = InMemoryAttendanceWriter(store, self._pending)
        self.outbox = InMemoryOutbox(
            self._pending,
            fail_on_add=fail_on_outbox_add,
        )

    def commit(self) -> None:
        if self._finished:
            raise RuntimeError("The unit of work has already finished.")

        if self._fail_on_commit:
            raise RuntimeError("Simulated commit failure.")

        self._store.events.update(self._pending.events)
        self._store.conflicts.extend(self._pending.conflicts)
        self._store.outbox.extend(self._pending.outbox)

        self._clear_pending()
        self._finished = True
        self.commits += 1

    def rollback(self) -> None:
        if self._finished:
            return

        self._clear_pending()
        self._finished = True
        self.rollbacks += 1

    def _clear_pending(self) -> None:
        self._pending.events.clear()
        self._pending.conflicts.clear()
        self._pending.outbox.clear()


class InMemoryUnitOfWorkFactory:
    """Create separate transactions sharing one committed store."""

    def __init__(self, store: InMemoryAttendanceStore) -> None:
        self.store = store
        self.opened = 0
        self.fail_on_commit = False
        self._created: list[InMemoryUnitOfWork] = []
        self.fail_on_outbox_add = False

    def __call__(self) -> InMemoryUnitOfWork:
        uow = InMemoryUnitOfWork(
            self.store,
            fail_on_commit=self.fail_on_commit,
            fail_on_outbox_add=self.fail_on_outbox_add,
        )
        self._created.append(uow)
        self.opened += 1
        return uow

    @property
    def commits(self) -> int:
        return sum(uow.commits for uow in self._created)

    @property
    def rollbacks(self) -> int:
        return sum(uow.rollbacks for uow in self._created)


class FakeStationAuthenticator(StationAuthenticator):
    """Resolve test tokens without using real authentication services."""

    def __init__(
        self,
        mapping: Mapping[str, AuthenticatedStation],
    ) -> None:
        self._mapping = dict(mapping)

    def authenticate(
        self,
        bearer_token: str,
    ) -> AuthenticatedStation | None:
        return self._mapping.get(bearer_token)


class InMemoryAttendanceReader(AttendanceReader):
    """Read committed events using the history query contract."""

    def __init__(self, store: InMemoryAttendanceStore) -> None:
        self._store = store

    def list_by_employee(
        self,
        employee_ref: UUID,
        occurred_from: datetime,
        occurred_to: datetime,
        limit: int,
        offset: int,
    ) -> HistoryPage:
        records = [
            record
            for record in self._store.events.values()
            if record.event.employee_ref == employee_ref
            and occurred_from <= record.event.occurred_at < occurred_to
        ]
        records.sort(
            key=lambda record: (
                record.event.occurred_at,
                record.event.event_id,
            )
        )

        page = records[offset : offset + limit + 1]
        items = tuple(
            AttendanceEventView(
                event_id=record.event.event_id,
                station_id=record.event.station_id,
                direction=record.event.direction,
                occurred_at=record.event.occurred_at.astimezone(UTC),
                received_at=record.received_at.astimezone(UTC),
                evidence_level=record.event.evidence_level,
            )
            for record in page[:limit]
        )

        return HistoryPage(
            items=items,
            has_more=len(page) > limit,
        )
