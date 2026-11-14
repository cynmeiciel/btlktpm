import sys
from types import ModuleType

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

from tmc_attendance.adapters.outbound.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)


def _install_adapter_modules(monkeypatch: pytest.MonkeyPatch) -> list[Connection]:
    connections: list[Connection] = []

    class ConnectionBoundAdapter:
        def __init__(self, connection: Connection) -> None:
            connections.append(connection)

    repository_module = ModuleType(
        "tmc_attendance.adapters.outbound.persistence.attendance_repository"
    )
    repository_module.PostgresAttendanceRepository = ConnectionBoundAdapter  # type: ignore[attr-defined]
    outbox_module = ModuleType("tmc_attendance.adapters.outbound.persistence.outbox")
    outbox_module.PostgresOutbox = ConnectionBoundAdapter  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules,
        repository_module.__name__,
        repository_module,
    )
    monkeypatch.setitem(sys.modules, outbox_module.__name__, outbox_module)
    return connections


def test_unit_of_work_shares_connection_and_commits_or_rolls_back(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter_connections = _install_adapter_modules(monkeypatch)
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE sample (value INTEGER NOT NULL)"))

        with SqlAlchemyUnitOfWork(engine) as uow:
            assert uow._connection is not None
            connection = uow._connection
            assert adapter_connections[0] is adapter_connections[1]
            assert adapter_connections[0] is connection
            connection.execute(text("INSERT INTO sample (value) VALUES (1)"))
            uow.commit()

        with SqlAlchemyUnitOfWork(engine) as uow:
            assert uow._connection is not None
            connection = uow._connection
            connection.execute(text("INSERT INTO sample (value) VALUES (2)"))

        with engine.connect() as connection:
            values = connection.execute(text("SELECT value FROM sample ORDER BY value"))
            assert values.scalars().all() == [1]
    finally:
        engine.dispose()
