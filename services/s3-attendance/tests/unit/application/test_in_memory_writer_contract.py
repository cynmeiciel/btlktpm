"""Run the shared writer contract against the in-memory adapter."""

import pytest

from tests.contracts.attendance_writer_contract import AttendanceWriterContract
from tests.fakes import (
    InMemoryAttendanceStore,
    InMemoryUnitOfWorkFactory,
)
from tmc_attendance.application.ports import UnitOfWorkFactory


class TestInMemoryWriter(AttendanceWriterContract):
    @pytest.fixture
    def uow_factory(self) -> UnitOfWorkFactory:
        return InMemoryUnitOfWorkFactory(InMemoryAttendanceStore())
