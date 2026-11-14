"""SQLAlchemy implementation of the application's unit-of-work port."""

from types import TracebackType
from typing import Self

from sqlalchemy import Connection, Engine
from sqlalchemy.engine import Transaction

from tmc_attendance.application.ports import AttendanceWriter, OutboxPort, UnitOfWork


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Share one connection and transaction between persistence adapters."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._connection: Connection | None = None
        self._transaction: Transaction | None = None
        self.attendance: AttendanceWriter
        self.outbox: OutboxPort

    def __enter__(self) -> Self:
        connection = self._engine.connect()
        try:
            transaction = connection.begin()
            self._connection = connection
            self._transaction = transaction

            # These adapters are added in T3.3 and T3.4; import only when opening
            # a unit of work so this module remains importable before those tasks land.
            from tmc_attendance.adapters.outbound.persistence.attendance_repository import (  # type: ignore[import-untyped]
                PostgresAttendanceRepository,
            )
            from tmc_attendance.adapters.outbound.persistence.outbox import (  # type: ignore[import-untyped]
                PostgresOutbox,
            )

            self.attendance = PostgresAttendanceRepository(connection)
            self.outbox = PostgresOutbox(connection)
        except Exception:
            if self._transaction is not None and self._transaction.is_active:
                self._transaction.rollback()
            self._connection = None
            self._transaction = None
            connection.close()
            raise

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            super().__exit__(exc_type, exc_value, traceback)
        finally:
            if self._connection is not None:
                self._connection.close()
            self._connection = None
            self._transaction = None

    def commit(self) -> None:
        if self._transaction is None or not self._transaction.is_active:
            raise RuntimeError("Cannot commit without an active unit-of-work transaction.")
        self._transaction.commit()

    def rollback(self) -> None:
        if self._transaction is not None and self._transaction.is_active:
            self._transaction.rollback()
