"""HTTP authentication helpers: station bearer tokens and the M2 actor-header stub."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status

from tmc_attendance.adapters.inbound.http.dependencies import (
    ApiDependencies,
    get_api_dependencies,
)
from tmc_attendance.application.dto import AuthenticatedStation
from tmc_attendance.application.ports import StationAuthenticator
from tmc_attendance.domain.access import ActorContext, Role

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


def read_actor(request: Request) -> ActorContext:
    """Build the actor from proxy-injected headers (M2 stub, docs/03-api-contract.md §3).

    Used as a route dependency so a missing actor yields 401 before query validation.
    """
    actor_id_value = request.headers.get("X-Actor-Id")
    roles_value = request.headers.get("X-Actor-Roles")
    employee_ref_value = request.headers.get("X-Actor-Employee-Ref")

    if not actor_id_value or roles_value is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Actor authentication required",
        )

    try:
        actor_id = UUID(actor_id_value)
        employee_ref = UUID(employee_ref_value) if employee_ref_value is not None else None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid actor identity",
        ) from None

    roles: set[Role] = set()
    for raw_role in roles_value.split(","):
        try:
            roles.add(Role(raw_role.strip()))
        except ValueError:
            continue

    return ActorContext(
        actor_id=actor_id,
        employee_ref=employee_ref,
        roles=frozenset(roles),
    )
