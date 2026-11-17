from uuid import UUID

from fastapi import HTTPException, Request

from tmc_attendance.domain.access import ActorContext, Role


def read_actor(request: Request) -> ActorContext:
    actor_id_value = request.headers.get("X-Actor-Id")
    roles_value = request.headers.get("X-Actor-Roles")
    employee_ref_value = request.headers.get("X-Actor-Employee-Ref")

    if not actor_id_value or roles_value is None:
        raise HTTPException(
            status_code=401,
            detail="Actor authentication required",
        )

    try:
        actor_id = UUID(actor_id_value)
        employee_ref = (
            UUID(employee_ref_value)
            if employee_ref_value is not None
            else None
        )
    except ValueError:
        raise HTTPException(
            status_code=401,
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
