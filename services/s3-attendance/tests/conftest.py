"""Shared test infrastructure (T0.5).

- Markers are assigned from the top-level test directory; never mark tests by hand.
- Database fixtures read URLs from ``DatabaseAdminSettings`` and skip when they are
  missing, unless ``TMC_REQUIRE_DB=1`` (set in CI), in which case they fail.
  See docs/05-testing-strategy.md §1.
"""

import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine, text

from tmc_attendance.bootstrap.config import DatabaseAdminSettings

TESTS_DIR = Path(__file__).parent
LAYER_MARKERS = frozenset({"unit", "api", "integration", "e2e"})
ATTENDANCE_SCHEMA = "attendance"
NEVER_TRUNCATE = frozenset({"alembic_version"})


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        part = item.path.relative_to(TESTS_DIR).parts[0]
        if part in LAYER_MARKERS:
            item.add_marker(getattr(pytest.mark, part))


@dataclass(frozen=True, slots=True)
class DatabaseUrls:
    owner: str
    app: str
    reader: str


def _db_required() -> bool:
    # The single sanctioned os.environ read in the repo (docs/07-conventions.md §4).
    return os.environ.get("TMC_REQUIRE_DB") == "1"


@pytest.fixture(scope="session")
def database_urls() -> DatabaseUrls:
    settings = DatabaseAdminSettings()
    missing = [
        name
        for name, value in (
            ("TMC_S3_MIGRATION_DATABASE_URL", settings.migration_database_url),
            ("TMC_S3_DATABASE_URL", settings.database_url),
            ("TMC_S3_READER_DATABASE_URL", settings.reader_database_url),
        )
        if not value
    ]
    if missing:
        message = f"database not configured: {', '.join(missing)} not set"
        if _db_required():
            pytest.fail(f"{message} (TMC_REQUIRE_DB=1)")
        pytest.skip(message)
    assert settings.migration_database_url
    assert settings.database_url
    assert settings.reader_database_url
    return DatabaseUrls(
        owner=settings.migration_database_url,
        app=settings.database_url,
        reader=settings.reader_database_url,
    )


def _engine(url: str) -> Iterator[Engine]:
    engine = create_engine(url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def owner_engine(database_urls: DatabaseUrls) -> Iterator[Engine]:
    """Role ``s3_attendance_owner``: schema setup and cleanup only."""
    yield from _engine(database_urls.owner)


@pytest.fixture(scope="session")
def app_engine(database_urls: DatabaseUrls) -> Iterator[Engine]:
    """Role ``s3_attendance_app``: same privileges as production; use for code under test."""
    yield from _engine(database_urls.app)


@pytest.fixture(scope="session")
def reader_engine(database_urls: DatabaseUrls) -> Iterator[Engine]:
    """Role ``s4_reporting_reader``: simulated S4, may only read the v1 view."""
    yield from _engine(database_urls.reader)


@pytest.fixture
def clean_db(owner_engine: Engine) -> None:
    """Empty every ``attendance`` table before the test (no rollback trick: code under test
    commits for real, docs/04-database.md §7)."""
    truncate_attendance_tables(owner_engine)


def truncate_attendance_tables(owner_engine: Engine) -> None:
    """TRUNCATE every table in the ``attendance`` schema except Alembic's version table.

    Tables are discovered from the catalog, so this works before migration 0001 exists
    and keeps working as later migrations add tables.
    """
    with owner_engine.begin() as conn:
        tables = conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = :schema ORDER BY tablename"),
            {"schema": ATTENDANCE_SCHEMA},
        ).scalars()
        quote = owner_engine.dialect.identifier_preparer.quote
        targets = [
            f"{quote(ATTENDANCE_SCHEMA)}.{quote(name)}"
            for name in tables
            if name not in NEVER_TRUNCATE
        ]
        if targets:
            conn.execute(text(f"TRUNCATE {', '.join(targets)}"))
