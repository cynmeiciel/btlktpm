"""HTTP authentication helpers for station requests."""

from fastapi import HTTPException, Request, status

from tmc_attendance.application.dto import AuthenticatedStation
from tmc_attendance.application.ports import StationAuthenticator


def authenticate_station(
    request: Request, authenticator: StationAuthenticator
) -> AuthenticatedStation:
    """Authenticate the request's bearer token without exposing it in errors or logs."""
    authorization = request.headers.get("Authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if (
        not separator
        or scheme.lower() != "bearer"
        or not token
        or token != token.strip()
        or any(character.isspace() for character in token)
    ):
        raise _unauthorized()

    station = authenticator.authenticate(token)
    if station is None:
        raise _unauthorized()
    return station


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid station credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
