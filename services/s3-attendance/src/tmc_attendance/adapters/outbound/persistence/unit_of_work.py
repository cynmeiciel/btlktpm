"""SQLAlchemy implementation of the application's unit-of-work port."""

from collections.abc import Callable
from importlib import import_module
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

            from tmc_attendance.adapters.outbound.persistence.attendance_repository import (
                PostgresAttendanceRepository,
            )

            self.attendance = PostgresAttendanceRepository(connection)
            outbox_module = import_module("tmc_attendance.adapters.outbound.persistence.outbox")
            outbox_factory: Callable[[Connection], OutboxPort] = outbox_module.__dict__[
                "PostgresOutbox"
            ]
            self.outbox = outbox_factory(connection)
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
