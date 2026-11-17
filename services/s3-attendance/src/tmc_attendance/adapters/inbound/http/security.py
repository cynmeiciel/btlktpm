"""HTTP authentication helpers for station requests."""

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from tmc_attendance.adapters.inbound.http.dependencies import (
    ApiDependencies,
    get_api_dependencies,
)
from tmc_attendance.application.dto import AuthenticatedStation
from tmc_attendance.application.ports import StationAuthenticator

logger = logging.getLogger(__name__)


def require_station(
    request: Request,
    deps: Annotated[ApiDependencies, Depends(get_api_dependencies)],
) -> AuthenticatedStation:
    """Authenticate before FastAPI validates the request body."""
    authenticator = deps.station_authenticator
    if authenticator is None:
        logger.error("Station authenticator is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unavailable",
        )
    return authenticate_station(request, authenticator)


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
