"""Tests for committed attendance history queries."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from tests.factories import make_event
from tests.fakes import (
    InMemoryAttendanceReader,
    InMemoryAttendanceStore,
    InMemoryUnitOfWorkFactory,
    StoredAttendanceEvent,
)
from tmc_attendance.domain.dedup import compute_payload_hash
from tmc_attendance.domain.model import AttendanceEvent

START = datetime(2026, 11, 3, 0, 0, tzinfo=UTC)
END = START + timedelta(days=1)


def seed_event(
    store: InMemoryAttendanceStore,
    event: AttendanceEvent,
) -> None:
    """Populate committed test data without exercising the write path."""
    store.events[event.event_id] = StoredAttendanceEvent(
        event=event,
        payload_hash=compute_payload_hash(event),
        received_at=END,
    )


def test_reader_does_not_expose_uncommitted_events() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    reader = InMemoryAttendanceReader(store)
    event = make_event(occurred_at=START)

    with factory() as uow:
        uow.attendance.insert_if_absent(
            event,
            compute_payload_hash(event),
            END,
        )

        before_commit = reader.list_by_employee(event.employee_ref, START, END, limit=50, offset=0)
        assert before_commit.items == ()

        uow.commit()

    after_commit = reader.list_by_employee(event.employee_ref, START, END, limit=50, offset=0)
    assert [item.event_id for item in after_commit.items] == [event.event_id]


def test_reader_filters_employee_and_half_open_time_range() -> None:
    store = InMemoryAttendanceStore()
    included = make_event(event_id=UUID(int=1), occurred_at=START)
    events = [
        included,
        make_event(event_id=UUID(int=2), occurred_at=END),
        make_event(
            event_id=UUID(int=3),
            occurred_at=START - timedelta(microseconds=1),
        ),
        make_event(
            event_id=UUID(int=4),
            employee_ref=UUID(int=999),
            occurred_at=START,
        ),
    ]
    for event in events:
        seed_event(store, event)

    page = InMemoryAttendanceReader(store).list_by_employee(
        included.employee_ref, START, END, limit=50, offset=0
    )

    assert [item.event_id for item in page.items] == [included.event_id]
    assert page.has_more is False


def test_reader_orders_and_paginates_without_missing_events() -> None:
    store = InMemoryAttendanceStore()
    first = make_event(event_id=UUID(int=1), occurred_at=START)
    second = make_event(event_id=UUID(int=2), occurred_at=START)
    third = make_event(
        event_id=UUID(int=3),
        occurred_at=START + timedelta(seconds=1),
    )
    for event in [third, second, first]:
        seed_event(store, event)
    reader = InMemoryAttendanceReader(store)

    first_page = reader.list_by_employee(first.employee_ref, START, END, limit=2, offset=0)
    second_page = reader.list_by_employee(first.employee_ref, START, END, limit=2, offset=2)

    assert [item.event_id for item in first_page.items] == [
        first.event_id,
        second.event_id,
    ]
    assert first_page.has_more is True
    assert [item.event_id for item in second_page.items] == [third.event_id]
    assert second_page.has_more is False


def test_reader_returns_empty_page_beyond_available_records() -> None:
    store = InMemoryAttendanceStore()
    event = make_event(occurred_at=START)
    seed_event(store, event)

    page = InMemoryAttendanceReader(store).list_by_employee(
        event.employee_ref, START, END, limit=2, offset=10
    )

    assert page.items == ()
    assert page.has_more is False
