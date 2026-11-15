"""The composition root wires a working app without touching the database."""

import pytest

from tmc_attendance.adapters.inbound.http.app import create_app
from tmc_attendance.adapters.outbound.persistence.health import PostgresHealthProbe
from tmc_attendance.adapters.outbound.station_auth import StaticTokenStationAuthenticator
from tmc_attendance.bootstrap.config import Settings
from tmc_attendance.bootstrap.container import build_api_dependencies

URL = "postgresql+psycopg://u:p@127.0.0.1:1/tmc"


def test_settings_read_environment_and_parse_station_tokens_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TMC_S3_DATABASE_URL", URL)
    monkeypatch.setenv("TMC_S3_STATION_TOKENS", '{"BD-G01-IN": "' + "ab" * 32 + '"}')
    monkeypatch.setenv("TMC_S3_MAX_BATCH_SIZE", "42")

    settings = Settings()  # values come from the environment

    assert settings.database_url == URL
    assert settings.station_tokens == {"BD-G01-IN": "ab" * 32}
    assert settings.max_batch_size == 42


def test_build_api_dependencies_uses_postgres_probe() -> None:
    deps = build_api_dependencies(Settings(database_url=URL))

    assert isinstance(deps.health, PostgresHealthProbe)
    assert isinstance(deps.station_authenticator, StaticTokenStationAuthenticator)


def test_app_exposes_health_routes() -> None:
    app = create_app(build_api_dependencies(Settings(database_url=URL)))

    assert {"/health/live", "/health/ready"} <= set(app.openapi()["paths"])
