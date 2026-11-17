"""Run the attendance-writer contract against PostgreSQL through the real unit of work."""

from collections.abc import Callable

import pytest
from sqlalchemy import Engine, text

from tests.contracts.attendance_writer_contract import AttendanceWriterContract
from tmc_attendance.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from tmc_attendance.application.ports import UnitOfWorkFactory


class TestPostgresWriter(AttendanceWriterContract):
    @pytest.fixture
    def uow_factory(self, app_engine: Engine) -> UnitOfWorkFactory:
        return lambda: SqlAlchemyUnitOfWork(app_engine)

    @pytest.fixture
    def count_conflicts(self, owner_engine: Engine) -> Callable[[], int]:
        def count() -> int:
            with owner_engine.connect() as connection:
                return int(
                    connection.execute(
                        text("SELECT count(*) FROM attendance.event_conflict")
                    ).scalar_one()
                )

        return count
