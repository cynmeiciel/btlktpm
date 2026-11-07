"""PostgresHealthProbe against a real and an unreachable database."""

import time

from sqlalchemy import Engine, create_engine

from tmc_attendance.adapters.outbound.persistence.health import PostgresHealthProbe


def test_ready_when_database_answers(app_engine: Engine) -> None:
    assert PostgresHealthProbe(app_engine).is_ready() is True


def test_not_ready_and_does_not_hang_when_database_is_unreachable() -> None:
    engine = create_engine(
        "postgresql+psycopg://nobody:nothing@127.0.0.1:1/tmc",
        connect_args={"connect_timeout": 2},
    )
    started = time.monotonic()
    try:
        assert PostgresHealthProbe(engine).is_ready() is False
    finally:
        engine.dispose()

    assert time.monotonic() - started < 5
