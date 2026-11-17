"""Alembic environment for S3 Attendance.

Runs as role ``s3_attendance_owner`` (``TMC_S3_MIGRATION_DATABASE_URL``). The schema
``attendance`` itself is created by ``infra/postgres/init/01-roles.sql``; migrations only
manage objects inside it, and the version table lives there too.
"""

from alembic import context
from sqlalchemy import create_engine, pool

from tmc_attendance.adapters.outbound.persistence.tables import metadata
from tmc_attendance.bootstrap.config import DatabaseAdminSettings

SCHEMA = "attendance"

target_metadata = metadata


def _include_name(name: str | None, type_: str, _parent_names: object) -> bool:
    """Autogenerate compares only the ``attendance`` schema owned by S3 (ADR02)."""
    if type_ == "schema":
        return name == SCHEMA
    return True


def _migration_url() -> str:
    url = DatabaseAdminSettings().migration_database_url
    if not url:
        raise RuntimeError(
            "TMC_S3_MIGRATION_DATABASE_URL is not set (see services/s3-attendance/README.md)"
        )
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_migration_url(),
        target_metadata=target_metadata,
        version_table_schema=SCHEMA,
        include_schemas=True,
        include_name=_include_name,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_migration_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=SCHEMA,
            include_schemas=True,
            include_name=_include_name,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
