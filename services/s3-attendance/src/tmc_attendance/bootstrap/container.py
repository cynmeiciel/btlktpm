"""Composition root: the only place where concrete adapters are created and wired."""

from sqlalchemy import Engine, create_engine

from tmc_attendance.adapters.inbound.http.dependencies import ApiDependencies
from tmc_attendance.adapters.outbound.persistence.health import PostgresHealthProbe
from tmc_attendance.adapters.outbound.station_auth import StaticTokenStationAuthenticator
from tmc_attendance.bootstrap.config import Settings


def create_app_engine(settings: Settings) -> Engine:
    """Engine for the runtime role ``s3_attendance_app``."""
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        connect_args={"connect_timeout": settings.db_connect_timeout_seconds},
    )


def build_api_dependencies(settings: Settings) -> ApiDependencies:
    """Wire real adapters into what the HTTP adapter needs."""
    engine = create_app_engine(settings)
    return ApiDependencies(
        health=PostgresHealthProbe(engine),
        station_authenticator=StaticTokenStationAuthenticator(settings.station_tokens),
        max_batch_size=settings.max_batch_size,
    )
