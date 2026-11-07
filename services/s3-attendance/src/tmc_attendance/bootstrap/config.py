"""Configuration read from environment variables (and a local ``.env`` file).

Only this module reads configuration from the environment. Values are passed to
constructors elsewhere (docs/07-conventions.md §4).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration of the S3 Attendance application."""

    model_config = SettingsConfigDict(env_prefix="TMC_S3_", env_file=".env", extra="ignore")

    database_url: str
    """``TMC_S3_DATABASE_URL`` — role ``s3_attendance_app``. Required."""

    station_tokens: dict[str, str] = {}
    """``TMC_S3_STATION_TOKENS`` — JSON map ``stationId -> sha256(token)`` (hex)."""

    max_future_skew_seconds: int = 300
    """``TMC_S3_MAX_FUTURE_SKEW_SECONDS`` — events further in the future are rejected."""

    max_batch_size: int = 500
    """``TMC_S3_MAX_BATCH_SIZE`` — maximum number of events per batch request."""

    log_level: str = "INFO"
    """``TMC_S3_LOG_LEVEL``."""

    db_connect_timeout_seconds: int = 3
    """``TMC_S3_DB_CONNECT_TIMEOUT_SECONDS`` — keeps ``/health/ready`` from hanging."""


class DatabaseAdminSettings(BaseSettings):
    """Database URLs for tooling: Alembic migrations and the test fixtures.

    Every field is optional so that constructing the settings never fails; each
    consumer decides what a missing URL means (Alembic raises, tests skip or fail).
    """

    model_config = SettingsConfigDict(env_prefix="TMC_S3_", env_file=".env", extra="ignore")

    migration_database_url: str | None = None
    """``TMC_S3_MIGRATION_DATABASE_URL`` — role ``s3_attendance_owner``."""

    database_url: str | None = None
    """``TMC_S3_DATABASE_URL`` — role ``s3_attendance_app`` (same role as the running app)."""

    reader_database_url: str | None = None
    """``TMC_S3_READER_DATABASE_URL`` — role ``s4_reporting_reader`` (simulated S4)."""
