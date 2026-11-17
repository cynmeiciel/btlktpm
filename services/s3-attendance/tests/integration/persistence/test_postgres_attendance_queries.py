"""PostgresAttendanceQueries against a real database (docs/05-testing-strategy.md §3)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Engine

from tests.factories import make_event
from tmc_attendance.adapters.outbound.persistence.attendance_queries import (
    PostgresAttendanceQueries,
)
from tmc_attendance.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from tmc_attendance.domain.dedup import compute_payload_hash
from tmc_attendance.domain.model import AttendanceEvent

EMPLOYEE = UUID("00000000-0000-0000-0000-00000000e001")
OTHER_EMPLOYEE = UUID("00000000-0000-0000-0000-00000000e002")
FROM = datetime(2026, 11, 3, 0, 0, tzinfo=UTC)
TO = datetime(2026, 11, 4, 0, 0, tzinfo=UTC)
RECEIVED_AT = datetime(2026, 11, 4, 1, 0, tzinfo=UTC)


def _event(n: int, employee_ref: UUID, occurred_at: datetime) -> AttendanceEvent:
    return make_event(
        event_id=UUID(int=n),
        attempt_id=UUID(int=1000 + n),
        employee_ref=employee_ref,
        occurred_at=occurred_at,
        local_sequence=n,
    )


def _seed(app_engine: Engine, *events: AttendanceEvent) -> None:
    with SqlAlchemyUnitOfWork(app_engine) as uow:
        for event in events:
            uow.attendance.insert_if_absent(event, compute_payload_hash(event), RECEIVED_AT)
        uow.commit()


def test_filters_by_employee_and_half_open_range(app_engine: Engine) -> None:
    at_from = _event(1, EMPLOYEE, FROM)
    inside = _event(2, EMPLOYEE, FROM + timedelta(hours=8))
    before_from = _event(3, EMPLOYEE, FROM - timedelta(microseconds=1))
    at_to = _event(4, EMPLOYEE, TO)
    other_employee = _event(5, OTHER_EMPLOYEE, FROM + timedelta(hours=8))
    _seed(app_engine, at_from, inside, before_from, at_to, other_employee)

    page = PostgresAttendanceQueries(app_engine).list_by_employee(
        EMPLOYEE, FROM, TO, limit=50, offset=0
    )

    assert [item.event_id for item in page.items] == [at_from.event_id, inside.event_id]
    assert page.has_more is False
    assert all(item.occurred_at.tzinfo == UTC for item in page.items)
    assert page.items[1].occurred_at == inside.occurred_at


def test_pages_cover_every_event_once_in_stable_order(app_engine: Engine) -> None:
    same_instant = FROM + timedelta(hours=2)
    events = [
        _event(5, EMPLOYEE, FROM + timedelta(hours=1)),
        _event(4, EMPLOYEE, same_instant),
        _event(3, EMPLOYEE, same_instant),
        _event(2, EMPLOYEE, FROM + timedelta(hours=3)),
        _event(1, EMPLOYEE, FROM + timedelta(hours=4)),
    ]
    _seed(app_engine, *events)
    queries = PostgresAttendanceQueries(app_engine)

    pages = [
        queries.list_by_employee(EMPLOYEE, FROM, TO, limit=2, offset=offset) for offset in (0, 2, 4)
    ]

    seen = [item.event_id for page in pages for item in page.items]
    assert seen == [UUID(int=5), UUID(int=3), UUID(int=4), UUID(int=2), UUID(int=1)]
    assert [page.has_more for page in pages] == [True, True, False]


def test_has_more_is_false_when_page_is_exactly_full(app_engine: Engine) -> None:
    _seed(
        app_engine,
        _event(1, EMPLOYEE, FROM + timedelta(hours=1)),
        _event(2, EMPLOYEE, FROM + timedelta(hours=2)),
    )

    page = PostgresAttendanceQueries(app_engine).list_by_employee(
        EMPLOYEE, FROM, TO, limit=2, offset=0
    )

    assert len(page.items) == 2
    assert page.has_more is False
