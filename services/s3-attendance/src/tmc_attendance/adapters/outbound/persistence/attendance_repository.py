"""PostgreSQL implementation of the attendance writer port."""

from datetime import datetime

from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from tmc_attendance.adapters.outbound.persistence.tables import (
    attendance_event,
    event_conflict,
)
from tmc_attendance.application.dto import EventConflict
from tmc_attendance.application.ports import (
    AttendanceWriter,
    EventIdExists,
    Inserted,
    InsertOutcome,
)
from tmc_attendance.domain.model import AttendanceEvent
from tmc_attendance.domain.values import PayloadHash


class PostgresAttendanceRepository(AttendanceWriter):
    """Persist immutable events and conflict evidence on a caller-owned connection."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def insert_if_absent(
        self,
        event: AttendanceEvent,
        payload_hash: PayloadHash,
        received_at: datetime,
    ) -> InsertOutcome:
        statement = (
            insert(attendance_event)
            .values(
                event_id=event.event_id,
                attempt_id=event.attempt_id,
                employee_ref=event.employee_ref,
                station_id=event.station_id,
                direction=event.direction.value,
                occurred_at=event.occurred_at,
                received_at=received_at,
                local_sequence=event.local_sequence,
                evidence_level=event.evidence_level.value,
                schema_version=event.schema_version,
                payload_hash=payload_hash,
            )
            .on_conflict_do_nothing(index_elements=[attendance_event.c.event_id])
            .returning(attendance_event.c.event_id)
        )
        inserted_id = self._connection.execute(statement).scalar_one_or_none()
        if inserted_id is not None:
            return Inserted()

        existing_hash = self._connection.execute(
            select(attendance_event.c.payload_hash).where(
                attendance_event.c.event_id == event.event_id
            )
        ).scalar_one_or_none()
        if existing_hash is None:
            raise RuntimeError(
                "Attendance event conflicted during insert but was not found afterward."
            )

        return EventIdExists(PayloadHash(existing_hash))

    def record_conflict(self, conflict: EventConflict) -> None:
        statement = (
            insert(event_conflict)
            .values(
                conflict_id=conflict.conflict_id,
                event_id=conflict.event_id,
                station_id=conflict.station_id,
                kind=conflict.kind.value,
                incoming_payload=dict(conflict.incoming_payload),
                incoming_hash=conflict.incoming_hash,
                detected_at=conflict.detected_at,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    event_conflict.c.event_id,
                    event_conflict.c.kind,
                    event_conflict.c.incoming_hash,
                ]
            )
        )
        self._connection.execute(statement)
