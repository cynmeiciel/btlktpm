"""Tests for the fake station authenticator."""

from tests.factories import make_station
from tests.fakes import FakeStationAuthenticator


def test_known_token_resolves_to_its_station() -> None:
    station = make_station()
    authenticator = FakeStationAuthenticator({"test-token": station})

    assert authenticator.authenticate("test-token") == station


def test_unknown_token_is_not_authenticated() -> None:
    authenticator = FakeStationAuthenticator({})

    assert authenticator.authenticate("unknown-token") is None


def test_tokens_resolve_to_separate_stations() -> None:
    first = make_station("BD-G01-IN")
    second = make_station("LA-G02-OUT")
    authenticator = FakeStationAuthenticator(
        {
            "first-token": first,
            "second-token": second,
        }
    )

    assert authenticator.authenticate("first-token") == first
    assert authenticator.authenticate("second-token") == second
