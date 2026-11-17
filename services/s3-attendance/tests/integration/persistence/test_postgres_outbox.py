"""Postgres integration tests for the transactional outbox adapter."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Engine, select

from tmc_attendance.adapters.outbound.persistence.tables import outbox
from tmc_attendance.adapters.outbound.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)
from tmc_attendance.application.dto import OutboxMessage


def _message() -> OutboxMessage:
    return OutboxMessage(
        message_id=UUID("3b70779b-8766-4b1c-8e54-6a6e34d3a2f1"),
        aggregate_id=UUID("ec1ba3df-d0aa-4ca0-8d85-a3a6e82d1959"),
        message_type="AttendanceEventAccepted.v1",
        payload={"eventId": "c1ff8393-5c0c-4cce-b9f0-d20a00f56574"},
        occurred_at=datetime(2026, 11, 14, 10, 0, tzinfo=UTC),
    )


def test_add_stages_message_until_uow_commit(app_engine: Engine) -> None:
    message = _message()

    with SqlAlchemyUnitOfWork(app_engine) as uow:
        uow.outbox.add(message)
        uow.commit()

    with app_engine.connect() as connection:
        row = (
            connection.execute(select(outbox).where(outbox.c.message_id == message.message_id))
            .mappings()
            .one()
        )

    assert row["aggregate_id"] == message.aggregate_id
    assert row["message_type"] == message.message_type
    assert row["payload"] == dict(message.payload)
    assert row["occurred_at"] == message.occurred_at
    assert row["state"] == "PENDING"
    assert row["attempts"] == 0


def test_add_is_rolled_back_when_uow_exits_without_commit(app_engine: Engine) -> None:
    message = _message()

    with SqlAlchemyUnitOfWork(app_engine) as uow:
        uow.outbox.add(message)

    with app_engine.connect() as connection:
        count = connection.execute(
            select(outbox.c.message_id).where(outbox.c.message_id == message.message_id)
        ).scalar_one_or_none()

    assert count is None
