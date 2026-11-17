from sqlalchemy import create_engine, text

from tmc_attendance.adapters.outbound.persistence.attendance_repository import (
    PostgresAttendanceRepository,
)
from tmc_attendance.adapters.outbound.persistence.outbox import PostgresOutbox
from tmc_attendance.adapters.outbound.persistence.unit_of_work import (
    SqlAlchemyUnitOfWork,
)


def test_unit_of_work_shares_connection_and_commits_or_rolls_back() -> None:
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE sample (value INTEGER NOT NULL)"))

        with SqlAlchemyUnitOfWork(engine) as uow:
            assert uow._connection is not None
            connection = uow._connection
            assert isinstance(uow.attendance, PostgresAttendanceRepository)
            assert isinstance(uow.outbox, PostgresOutbox)
            assert uow.attendance._connection is uow.outbox._connection is connection
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
