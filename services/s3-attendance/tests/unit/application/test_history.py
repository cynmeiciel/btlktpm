from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from tests.factories import make_event
from tests.fakes import (
    InMemoryAttendanceReader,
    InMemoryAttendanceStore,
    StoredAttendanceEvent,
)
from tmc_attendance.application.dto import HistoryQuery
from tmc_attendance.application.errors import AccessDenied, InvalidQuery
from tmc_attendance.application.history import GetAttendanceHistoryUseCase
from tmc_attendance.domain.access import ActorContext, Role
from tmc_attendance.domain.dedup import compute_payload_hash
from tmc_attendance.domain.model import AttendanceEvent

START = datetime(2026, 11, 3, 0, 0, tzinfo=UTC)
END = START + timedelta(days=1)
EMPLOYEE_REF = UUID(int=1)
OTHER_EMPLOYEE_REF = UUID(int=2)


def _use_case_with_event() -> tuple[GetAttendanceHistoryUseCase, AttendanceEvent]:
    store = InMemoryAttendanceStore()
    event = make_event(employee_ref=EMPLOYEE_REF, occurred_at=START)
    store.events[event.event_id] = StoredAttendanceEvent(
        event=event,
        payload_hash=compute_payload_hash(event),
        received_at=END,
    )
    return GetAttendanceHistoryUseCase(InMemoryAttendanceReader(store)), event


def _actor(
    employee_ref: UUID | None,
    roles: frozenset[Role] = frozenset({Role.EMPLOYEE}),
) -> ActorContext:
    return ActorContext(actor_id=UUID(int=10), employee_ref=employee_ref, roles=roles)


def test_employee_can_read_own_history() -> None:
    use_case, event = _use_case_with_event()

    page = use_case.execute(
        HistoryQuery(EMPLOYEE_REF, START, END),
        _actor(EMPLOYEE_REF),
    )

    assert [item.event_id for item in page.items] == [event.event_id]
    assert page.has_more is False


def test_employee_cannot_read_another_employees_history() -> None:
    use_case, _ = _use_case_with_event()

    with pytest.raises(AccessDenied):
        use_case.execute(
            HistoryQuery(EMPLOYEE_REF, START, END),
            _actor(OTHER_EMPLOYEE_REF),
        )


def test_history_rejects_ranges_over_62_days() -> None:
    use_case, _ = _use_case_with_event()

    with pytest.raises(InvalidQuery):
        use_case.execute(
            HistoryQuery(
                EMPLOYEE_REF,
                START,
                START + timedelta(days=63),
            ),
            _actor(EMPLOYEE_REF),
        )
