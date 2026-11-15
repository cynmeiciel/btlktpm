"""Static station-token authentication using configured SHA-256 digests."""

import hashlib
import hmac
import re
from collections.abc import Mapping

from tmc_attendance.application.dto import AuthenticatedStation
from tmc_attendance.application.ports import StationAuthenticator
from tmc_attendance.domain.values import StationId, parse_station_id


class StaticTokenStationAuthenticator(StationAuthenticator):
    """Authenticate bearer tokens without retaining or logging the token itself."""

    def __init__(self, station_token_hashes: Mapping[str, str]) -> None:
        self._station_token_hashes = {
            parse_station_id(station_id): digest.lower()
            for station_id, digest in station_token_hashes.items()
        }
        digests = tuple(self._station_token_hashes.values())
        if any(re.fullmatch(r"[0-9a-f]{64}", digest) is None for digest in digests):
            raise ValueError("Station token hashes must be 64 hexadecimal characters")
        if len(set(digests)) != len(digests):
            raise ValueError("Each station must have a unique token hash")

    def authenticate(self, bearer_token: str) -> AuthenticatedStation | None:
        """Return the matching station, checking every configured digest."""
        token_hash = hashlib.sha256(bearer_token.encode("utf-8")).hexdigest()
        authenticated_station: StationId | None = None
        for station_id, expected_hash in self._station_token_hashes.items():
            if hmac.compare_digest(token_hash, expected_hash):
                authenticated_station = station_id
        if authenticated_station is None:
            return None
        return AuthenticatedStation(station_id=authenticated_station)
