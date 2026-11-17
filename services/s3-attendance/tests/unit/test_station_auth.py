import hashlib

import pytest

from tests.factories import SAMPLE_STATION_ID, SAMPLE_STATION_TOKEN
from tmc_attendance.adapters.outbound.station_auth import StaticTokenStationAuthenticator


def _authenticator() -> StaticTokenStationAuthenticator:
    token_hash = hashlib.sha256(SAMPLE_STATION_TOKEN.encode("utf-8")).hexdigest()
    return StaticTokenStationAuthenticator({SAMPLE_STATION_ID: token_hash})


def test_authenticates_the_configured_station_token() -> None:
    station = _authenticator().authenticate(SAMPLE_STATION_TOKEN)

    assert station is not None
    assert station.station_id == SAMPLE_STATION_ID


def test_rejects_an_unknown_station_token() -> None:
    station = _authenticator().authenticate("not-the-configured-token")

    assert station is None


@pytest.mark.parametrize(
    "token_hash",
    ["short", "g" * 64],
)
def test_rejects_invalid_configured_token_hash(token_hash: str) -> None:
    with pytest.raises(ValueError, match="64 hexadecimal characters"):
        StaticTokenStationAuthenticator({SAMPLE_STATION_ID: token_hash})
