"""Tests for transactional behavior of the in-memory unit of work."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from tests.factories import make_event
from tests.fakes import (
    InMemoryAttendanceStore,
    InMemoryUnitOfWorkFactory,
)
from tmc_attendance.application.dto import OutboxMessage
from tmc_attendance.application.ports import UnitOfWork
from tmc_attendance.domain.dedup import compute_payload_hash
from tmc_attendance.domain.model import AttendanceEvent

NOW = datetime(2026, 11, 3, 1, 0, tzinfo=UTC)


def stage_event_and_message(
    uow: UnitOfWork,
) -> tuple[AttendanceEvent, OutboxMessage]:
    """Stage related records without committing."""
    event = make_event()
    message = OutboxMessage(
        message_id=UUID(int=1),
        aggregate_id=event.event_id,
        message_type="AttendanceEventAccepted.v1",
        payload={"eventId": str(event.event_id)},
        occurred_at=NOW,
    )
    uow.attendance.insert_if_absent(
        event,
        compute_payload_hash(event),
        NOW,
    )
    uow.outbox.add(message)
    return event, message


def test_commit_publishes_event_and_outbox_together() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)

    with factory() as uow:
        event, message = stage_event_and_message(uow)

        assert store.count() == 0
        assert store.outbox == []

        uow.commit()

    assert store.events[event.event_id].event == event
    assert store.outbox == [message]
    assert factory.opened == 1
    assert factory.commits == 1
    assert factory.rollbacks == 0


def test_exit_without_commit_discards_event_and_outbox() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)

    with factory() as uow:
        stage_event_and_message(uow)

    assert store.count() == 0
    assert store.outbox == []
    assert factory.commits == 0
    assert factory.rollbacks == 1


def test_exception_discards_pending_changes_and_propagates() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)

    def process_with_error() -> None:
        with factory() as uow:
            stage_event_and_message(uow)
            raise ValueError("Processing failed.")

    with pytest.raises(ValueError, match="Processing failed"):
        process_with_error()

    assert store.count() == 0
    assert store.outbox == []
    assert factory.commits == 0
    assert factory.rollbacks == 1


def test_failed_commit_does_not_publish_pending_changes() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    factory.fail_on_commit = True

    def commit_transaction() -> None:
        with factory() as uow:
            stage_event_and_message(uow)
            uow.commit()

    with pytest.raises(RuntimeError, match="Simulated commit failure"):
        commit_transaction()

    assert store.count() == 0
    assert store.outbox == []
    assert factory.commits == 0
    assert factory.rollbacks == 1


def test_outbox_failure_discards_the_pending_event() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    factory.fail_on_outbox_add = True

    def process_transaction() -> None:
        with factory() as uow:
            stage_event_and_message(uow)
            uow.commit()

    with pytest.raises(RuntimeError, match="Simulated outbox failure"):
        process_transaction()

    assert store.count() == 0
    assert store.outbox == []
    assert factory.commits == 0
    assert factory.rollbacks == 1
