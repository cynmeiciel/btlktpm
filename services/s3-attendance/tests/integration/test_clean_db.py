"""The cleanup helper empties attendance tables but keeps Alembic's version table."""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text

from tests.conftest import truncate_attendance_tables

COUNT_SCRATCH = text("SELECT count(*) FROM attendance.t05_scratch")
COUNT_VERSIONS = text("SELECT count(*) FROM attendance.alembic_version")


@pytest.fixture
def seeded_tables(owner_engine: Engine) -> Iterator[int]:
    """Create a scratch table with rows; ensure ``alembic_version`` exists. Yields its row count.

    ``alembic_version`` is only created (and later dropped) when no migration has run yet,
    so the test never damages a migrated database.
    """
    with owner_engine.begin() as conn:
        conn.execute(text("CREATE TABLE attendance.t05_scratch (id int PRIMARY KEY)"))
        conn.execute(text("INSERT INTO attendance.t05_scratch VALUES (1), (2)"))
        created_versions = (
            conn.execute(text("SELECT to_regclass('attendance.alembic_version')")).scalar() is None
        )
        if created_versions:
            conn.execute(text("CREATE TABLE attendance.alembic_version (version_num varchar(32))"))
            conn.execute(text("INSERT INTO attendance.alembic_version VALUES ('t05')"))
        versions = conn.execute(COUNT_VERSIONS).scalar_one()
    try:
        yield versions
    finally:
        with owner_engine.begin() as conn:
            conn.execute(text("DROP TABLE attendance.t05_scratch"))
            if created_versions:
                conn.execute(text("DROP TABLE attendance.alembic_version"))


def test_truncates_attendance_tables_but_keeps_alembic_version(
    owner_engine: Engine, seeded_tables: int
) -> None:
    truncate_attendance_tables(owner_engine)

    with owner_engine.connect() as conn:
        assert conn.execute(COUNT_SCRATCH).scalar_one() == 0
        assert conn.execute(COUNT_VERSIONS).scalar_one() == seeded_tables
