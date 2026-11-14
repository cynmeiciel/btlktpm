"""Behavioural contract shared by every ``AttendanceWriter`` implementation."""

from datetime import UTC, datetime

import pytest

from tests.factories import make_event
from tmc_attendance.application.ports import (
    EventIdExists,
    Inserted,
    UnitOfWorkFactory,
)
from tmc_attendance.domain.dedup import compute_payload_hash

RECEIVED_AT = datetime(2026, 11, 14, 10, 0, tzinfo=UTC)


class AttendanceWriterContract:
    @pytest.fixture
    def uow_factory(self) -> UnitOfWorkFactory:
        raise NotImplementedError("subclass must provide a UnitOfWorkFactory")

    def test_first_insert_returns_inserted(self, uow_factory: UnitOfWorkFactory) -> None:
        event = make_event()
        payload_hash = compute_payload_hash(event)

        with uow_factory() as uow:
            result = uow.attendance.insert_if_absent(event, payload_hash, RECEIVED_AT)
            assert isinstance(result, Inserted)
            uow.commit()

    def test_same_event_id_returns_event_id_exists_with_hash(
        self, uow_factory: UnitOfWorkFactory
    ) -> None:
        event = make_event()
        payload_hash = compute_payload_hash(event)
        with uow_factory() as uow:
            uow.attendance.insert_if_absent(event, payload_hash, RECEIVED_AT)
            uow.commit()

        with uow_factory() as uow:
            result = uow.attendance.insert_if_absent(event, payload_hash, RECEIVED_AT)

        assert result == EventIdExists(payload_hash)

    def test_nothing_visible_without_commit(self, uow_factory: UnitOfWorkFactory) -> None:
        event = make_event()
        payload_hash = compute_payload_hash(event)
        with uow_factory() as uow:
            result = uow.attendance.insert_if_absent(event, payload_hash, RECEIVED_AT)
            assert isinstance(result, Inserted)

        with uow_factory() as uow:
            result = uow.attendance.insert_if_absent(event, payload_hash, RECEIVED_AT)
            assert isinstance(result, Inserted)
            uow.commit()
