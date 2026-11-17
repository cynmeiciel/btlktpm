from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import Engine

from tmc_attendance.adapters.outbound.persistence.table import attendance_event
from tmc_attendance.application.dto import AttendanceEventView, HistoryPage
from tmc_attendance.application.ports import AttendanceReader
from tmc_attendance.domain.model import Direction, EvidenceLevel
from tmc_attendance.domain.values import StationId


class PostgresAttendanceQueries(AttendanceReader):
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def list_by_employee(
        self,
        employee_ref: UUID,
        occurred_from: datetime,
        occurred_to: datetime,
        limit: int,
        offset: int,
    ) -> HistoryPage:
        stmt = (
            sa.select(
                attendance_event.c.event_id,
                attendance_event.c.station_id,
                attendance_event.c.direction,
                attendance_event.c.occurred_at,
                attendance_event.c.received_at,
                attendance_event.c.evidence_level,
            )
            .where(
                attendance_event.c.employee_ref == employee_ref,
                attendance_event.c.occurred_at >= occurred_from,
                attendance_event.c.occurred_at < occurred_to,
            )
            .order_by(
                attendance_event.c.occurred_at,
                attendance_event.c.event_id,
            )
            .limit(limit + 1)
            .offset(offset)
        )

        with self._engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()

        has_more = len(rows) > limit
        items = tuple(
            AttendanceEventView(
                event_id=row["event_id"],
                station_id=StationId(row["station_id"]),
                direction=Direction(row["direction"]),
                occurred_at=row["occurred_at"].astimezone(UTC),
                received_at=row["received_at"].astimezone(UTC),
                evidence_level=EvidenceLevel(row["evidence_level"]),
            )
            for row in rows[:limit]
        )
        return HistoryPage(items=items, has_more=has_more)
