"""Authorization rules for attendance history."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    EMPLOYEE = "EMPLOYEE"
    SUPERVISOR = "SUPERVISOR"
    HR = "HR"
    SECURITY = "SECURITY"
    ADMIN = "ADMIN"
    EXECUTIVE = "EXECUTIVE"


@dataclass(frozen=True, slots=True)
class ActorContext:
    """Describe an authenticated actor and their assigned roles."""

    actor_id: UUID
    employee_ref: UUID | None
    roles: frozenset[Role]


def can_read_history(actor: ActorContext, target: UUID) -> bool:
    """Allow access to personal history or access granted by the HR role."""
    return actor.employee_ref == target or Role.HR in actor.roles
