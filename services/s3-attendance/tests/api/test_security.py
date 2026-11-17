import hashlib

from fastapi import Request
from fastapi.testclient import TestClient

from tests.factories import SAMPLE_STATION_ID, SAMPLE_STATION_TOKEN
from tests.fakes import FakeHealthProbe
from tmc_attendance.adapters.inbound.http.app import create_app
from tmc_attendance.adapters.inbound.http.dependencies import ApiDependencies
from tmc_attendance.adapters.inbound.http.security import authenticate_station
from tmc_attendance.adapters.outbound.station_auth import StaticTokenStationAuthenticator


def _client() -> TestClient:
    token_hash = hashlib.sha256(SAMPLE_STATION_TOKEN.encode("utf-8")).hexdigest()
    authenticator = StaticTokenStationAuthenticator({SAMPLE_STATION_ID: token_hash})
    app = create_app(
        ApiDependencies(
            health=FakeHealthProbe(),
            station_authenticator=authenticator,
        )
    )

    @app.get("/test-station-auth")
    def station_auth_route(request: Request) -> dict[str, str]:
        station = authenticate_station(request, authenticator)
        return {"stationId": station.station_id}

    return TestClient(app)


def test_missing_station_token_returns_401_with_bearer_challenge() -> None:
    response = _client().get("/test-station-auth")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_valid_station_token_authenticates_the_station() -> None:
    response = _client().get(
        "/test-station-auth",
        headers={"Authorization": f"Bearer {SAMPLE_STATION_TOKEN}"},
    )

    assert response.status_code == 200
    assert response.json() == {"stationId": SAMPLE_STATION_ID}


def test_invalid_station_token_is_not_returned_or_logged(caplog) -> None:
    token = "secret-invalid-station-token"
    response = _client().get(
        "/test-station-auth",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert token not in response.text
    assert token not in caplog.text
