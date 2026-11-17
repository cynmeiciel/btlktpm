from datetime import timedelta

from tmc_attendance.application.dto import HistoryPage, HistoryQuery
from tmc_attendance.application.errors import AccessDenied, InvalidQuery
from tmc_attendance.application.ports import AttendanceReader
from tmc_attendance.domain.access import ActorContext, can_read_history


class GetAttendanceHistoryUseCase:
    def __init__(self, reader: AttendanceReader) -> None:
        self._reader = reader

    def execute(
        self,
        query: HistoryQuery,
        actor: ActorContext,
    ) -> HistoryPage:
        self._validate(query)

        if not can_read_history(actor, query.employee_ref):
            raise AccessDenied

        return self._reader.list_by_employee(
            employee_ref=query.employee_ref,
            occurred_from=query.occurred_from,
            occurred_to=query.occurred_to,
            limit=query.limit,
            offset=query.offset,
        )

    @staticmethod
    def _validate(query: HistoryQuery) -> None:
        if query.occurred_from.utcoffset() is None or query.occurred_to.utcoffset() is None:
            raise InvalidQuery("from and to must include a timezone")

        if query.occurred_to <= query.occurred_from:
            raise InvalidQuery("to must be later than from")

        if query.occurred_to - query.occurred_from > timedelta(days=62):
            raise InvalidQuery("range must not exceed 62 days")

        if not 1 <= query.limit <= 200 or query.offset < 0:
            raise InvalidQuery("invalid pagination")
