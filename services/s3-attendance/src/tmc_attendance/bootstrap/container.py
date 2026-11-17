"""Composition root: the only place where concrete adapters are created and wired."""

from datetime import timedelta

from sqlalchemy import Engine, create_engine

from tmc_attendance.adapters.inbound.http.dependencies import ApiDependencies
from tmc_attendance.adapters.outbound.clock import SystemClock
from tmc_attendance.adapters.outbound.ids import Uuid4Generator
from tmc_attendance.adapters.outbound.persistence.attendance_queries import (
    PostgresAttendanceQueries,
)
from tmc_attendance.adapters.outbound.persistence.health import PostgresHealthProbe
from tmc_attendance.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from tmc_attendance.adapters.outbound.station_auth import StaticTokenStationAuthenticator
from tmc_attendance.application.history import GetAttendanceHistoryUseCase
from tmc_attendance.application.ingest_batch import IngestAttendanceBatchUseCase
from tmc_attendance.application.ingest_event import IngestAttendanceEventUseCase
from tmc_attendance.application.ports import UnitOfWork
from tmc_attendance.bootstrap.config import Settings
from tmc_attendance.domain.dedup import DeduplicationRule
from tmc_attendance.domain.policy import EventValidationPolicy


def create_app_engine(settings: Settings) -> Engine:
    """Engine for the runtime role ``s3_attendance_app``."""
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        connect_args={"connect_timeout": settings.db_connect_timeout_seconds},
    )


def build_api_dependencies(settings: Settings) -> ApiDependencies:
    """Create the runtime engine and wire every real adapter (used by ``main.py``)."""
    return wire_api_dependencies(create_app_engine(settings), settings)


def wire_api_dependencies(engine: Engine, settings: Settings) -> ApiDependencies:
    """Wire real adapters around an existing engine (E2E tests pass their own engine)."""

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(engine)

    ingest_event = IngestAttendanceEventUseCase(
        uow_factory,
        SystemClock(),
        Uuid4Generator(),
        EventValidationPolicy(timedelta(seconds=settings.max_future_skew_seconds)),
        DeduplicationRule(),
    )
    return ApiDependencies(
        health=PostgresHealthProbe(engine),
        station_authenticator=StaticTokenStationAuthenticator(settings.station_tokens),
        ingest_batch=IngestAttendanceBatchUseCase(ingest_event),
        max_batch_size=settings.max_batch_size,
        history=GetAttendanceHistoryUseCase(PostgresAttendanceQueries(engine)),
    )
