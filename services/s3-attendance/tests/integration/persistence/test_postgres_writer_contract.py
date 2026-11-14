"""Run the attendance-writer contract against PostgreSQL."""

from types import TracebackType
from typing import Self

import pytest
from sqlalchemy import Connection, Engine
from sqlalchemy.engine import Transaction

from tests.contracts.attendance_writer_contract import AttendanceWriterContract
from tmc_attendance.adapters.outbound.persistence.attendance_repository import (
    PostgresAttendanceRepository,
)
from tmc_attendance.application.dto import OutboxMessage
from tmc_attendance.application.ports import OutboxPort, UnitOfWork, UnitOfWorkFactory


class _UnusedOutbox(OutboxPort):
    def add(self, message: OutboxMessage) -> None:
        raise AssertionError("The AttendanceWriter contract must not write outbox messages.")


class _RepositoryUnitOfWork(UnitOfWork):
    """Provide transaction scope for repository contract tests, before T3.4 lands."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine
        self._connection: Connection | None = None
        self._transaction: Transaction | None = None
        self.attendance: PostgresAttendanceRepository
        self.outbox = _UnusedOutbox()

    def __enter__(self) -> Self:
        connection = self._engine.connect()
        try:
            self._transaction = connection.begin()
            self._connection = connection
            self.attendance = PostgresAttendanceRepository(connection)
        except Exception:
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
            raise RuntimeError("Cannot commit without an active transaction.")
        self._transaction.commit()

    def rollback(self) -> None:
        if self._transaction is not None and self._transaction.is_active:
            self._transaction.rollback()


class TestPostgresWriter(AttendanceWriterContract):
    @pytest.fixture
    def uow_factory(self, app_engine: Engine) -> UnitOfWorkFactory:
        return lambda: _RepositoryUnitOfWork(app_engine)
