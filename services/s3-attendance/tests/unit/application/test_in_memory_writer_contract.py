"""Run the shared writer contract against the in-memory adapter."""

from collections.abc import Callable

import pytest

from tests.contracts.attendance_writer_contract import AttendanceWriterContract
from tests.fakes import (
    InMemoryAttendanceStore,
    InMemoryUnitOfWorkFactory,
)
from tmc_attendance.application.ports import UnitOfWorkFactory


class TestInMemoryWriter(AttendanceWriterContract):
    @pytest.fixture
    def store(self) -> InMemoryAttendanceStore:
        return InMemoryAttendanceStore()

    @pytest.fixture
    def uow_factory(self, store: InMemoryAttendanceStore) -> UnitOfWorkFactory:
        return InMemoryUnitOfWorkFactory(store)

    @pytest.fixture
    def count_conflicts(self, store: InMemoryAttendanceStore) -> Callable[[], int]:
        return lambda: len(store.conflicts)
