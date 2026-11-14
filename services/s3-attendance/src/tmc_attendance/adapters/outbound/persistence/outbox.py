"""PostgreSQL implementation of the transactional outbox port."""

from sqlalchemy import Connection, insert

from tmc_attendance.adapters.outbound.persistence.tables import outbox
from tmc_attendance.application.dto import OutboxMessage
from tmc_attendance.application.ports import OutboxPort


class PostgresOutbox(OutboxPort):
    """Stage outbox messages on the unit of work's connection."""

    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def add(self, message: OutboxMessage) -> None:
        statement = insert(outbox).values(
            message_id=message.message_id,
            aggregate_id=message.aggregate_id,
            message_type=message.message_type,
            payload=dict(message.payload),
            occurred_at=message.occurred_at,
        )
        self._connection.execute(statement)
