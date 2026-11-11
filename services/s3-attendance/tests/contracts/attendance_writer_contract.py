"""Behavioral contract shared by attendance writer implementations."""

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import pytest

from tests.factories import make_event
from tmc_attendance.application.dto import EventConflict
from tmc_attendance.application.ports import (
    EventIdExists,
    Inserted,
    UnitOfWorkFactory,
)
from tmc_attendance.domain.dedup import ConflictKind, compute_payload_hash
from tmc_attendance.domain.model import Direction

RECEIVED_AT = datetime(2026, 11, 3, 1, 0, tzinfo=UTC)


class AttendanceWriterContract:
    @pytest.fixture
    def uow_factory(self) -> UnitOfWorkFactory:
        raise NotImplementedError("Subclass must provide a unit-of-work factory.")

    @pytest.fixture
    def count_conflicts(self) -> Callable[[], int]:
        """Return a function counting committed conflict records in the same storage."""
        raise NotImplementedError("Subclass must provide a committed conflict counter.")

    def test_first_insert_returns_inserted(
        self,
        uow_factory: UnitOfWorkFactory,
    ) -> None:
        event = make_event()
        payload_hash = compute_payload_hash(event)

        with uow_factory() as uow:
            outcome = uow.attendance.insert_if_absent(event, payload_hash, RECEIVED_AT)
            uow.commit()

        assert isinstance(outcome, Inserted)

    def test_same_event_id_returns_event_id_exists_with_hash(
        self,
        uow_factory: UnitOfWorkFactory,
    ) -> None:
        event = make_event()
        payload_hash = compute_payload_hash(event)
        with uow_factory() as uow:
            uow.attendance.insert_if_absent(event, payload_hash, RECEIVED_AT)
            uow.commit()

        with uow_factory() as uow:
            outcome = uow.attendance.insert_if_absent(event, payload_hash, RECEIVED_AT)
            uow.commit()

        assert isinstance(outcome, EventIdExists)
        assert outcome.existing_hash == payload_hash

    def test_nothing_visible_without_commit(
        self,
        uow_factory: UnitOfWorkFactory,
    ) -> None:
        event = make_event()
        payload_hash = compute_payload_hash(event)

        with uow_factory() as uow:
            uow.attendance.insert_if_absent(event, payload_hash, RECEIVED_AT)

        with uow_factory() as uow:
            outcome = uow.attendance.insert_if_absent(event, payload_hash, RECEIVED_AT)
            uow.commit()

        assert isinstance(outcome, Inserted)

    def test_same_conflict_recorded_twice_is_stored_once(
        self,
        uow_factory: UnitOfWorkFactory,
        count_conflicts: Callable[[], int],
    ) -> None:
        original = make_event()
        with uow_factory() as uow:
            uow.attendance.insert_if_absent(original, compute_payload_hash(original), RECEIVED_AT)
            uow.commit()

        changed = make_event(direction=Direction.OUT)
        for attempt in (1, 2):
            conflict = EventConflict(
                conflict_id=UUID(int=attempt),
                event_id=original.event_id,
                station_id=original.station_id,
                kind=ConflictKind.PAYLOAD_MISMATCH,
                incoming_payload={"direction": "OUT"},
                incoming_hash=compute_payload_hash(changed),
                detected_at=RECEIVED_AT,
            )
            with uow_factory() as uow:
                uow.attendance.record_conflict(conflict)
                uow.commit()

        assert count_conflicts() == 1
