"""Tests for buffered event and outbox writes."""

from datetime import UTC, datetime
from uuid import UUID

from tests.factories import make_event
from tests.fakes import (
    InMemoryAttendanceStore,
    InMemoryAttendanceWriter,
    InMemoryOutbox,
    StoredAttendanceEvent,
)
from tmc_attendance.application.dto import OutboxMessage
from tmc_attendance.application.ports import EventIdExists, Inserted
from tmc_attendance.domain.dedup import compute_payload_hash
from tmc_attendance.domain.model import Direction

NOW = datetime(2026, 11, 3, 1, 0, tzinfo=UTC)


def test_new_event_is_staged_without_changing_committed_store() -> None:
    store = InMemoryAttendanceStore()
    pending = InMemoryAttendanceStore()
    writer = InMemoryAttendanceWriter(store, pending)
    event = make_event()
    payload_hash = compute_payload_hash(event)

    outcome = writer.insert_if_absent(event, payload_hash, NOW)

    assert isinstance(outcome, Inserted)
    assert store.count() == 0
    assert pending.count() == 1
    assert pending.events[event.event_id] == StoredAttendanceEvent(
        event=event,
        payload_hash=payload_hash,
        received_at=NOW,
    )


def test_repeated_id_in_buffer_returns_existing_hash() -> None:
    store = InMemoryAttendanceStore()
    pending = InMemoryAttendanceStore()
    writer = InMemoryAttendanceWriter(store, pending)
    event = make_event()
    payload_hash = compute_payload_hash(event)
    writer.insert_if_absent(event, payload_hash, NOW)

    outcome = writer.insert_if_absent(event, payload_hash, NOW)

    assert isinstance(outcome, EventIdExists)
    assert outcome.existing_hash == payload_hash
    assert pending.count() == 1


def test_existing_committed_event_is_not_overwritten() -> None:
    store = InMemoryAttendanceStore()
    pending = InMemoryAttendanceStore()
    original = make_event()
    original_hash = compute_payload_hash(original)
    stored = StoredAttendanceEvent(original, original_hash, NOW)
    store.events[original.event_id] = stored
    writer = InMemoryAttendanceWriter(store, pending)
    changed = make_event(direction=Direction.OUT)

    outcome = writer.insert_if_absent(
        changed,
        compute_payload_hash(changed),
        NOW,
    )

    assert isinstance(outcome, EventIdExists)
    assert outcome.existing_hash == original_hash
    assert store.events[original.event_id] == stored
    assert pending.count() == 0


def test_outbox_message_is_staged_without_changing_committed_store() -> None:
    store = InMemoryAttendanceStore()
    pending = InMemoryAttendanceStore()
    outbox = InMemoryOutbox(pending)
    event = make_event()
    message = OutboxMessage(
        message_id=UUID(int=1),
        aggregate_id=event.event_id,
        message_type="AttendanceEventAccepted.v1",
        payload={"eventId": str(event.event_id)},
        occurred_at=NOW,
    )

    outbox.add(message)

    assert pending.outbox == [message]
    assert store.outbox == []
