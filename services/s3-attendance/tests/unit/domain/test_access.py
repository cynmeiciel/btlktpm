"""Tests for attendance history authorization."""

from uuid import UUID

import pytest

from tmc_attendance.domain.access import (
    ActorContext,
    Role,
    can_read_history,
)

ACTOR_ID = UUID(int=1)
OWN_EMPLOYEE_REF = UUID(int=2)
OTHER_EMPLOYEE_REF = UUID(int=3)


def test_employee_can_read_own_history() -> None:
    actor = ActorContext(
        actor_id=ACTOR_ID,
        employee_ref=OWN_EMPLOYEE_REF,
        roles=frozenset({Role.EMPLOYEE}),
    )

    assert can_read_history(actor, OWN_EMPLOYEE_REF) is True


@pytest.mark.parametrize(
    "role",
    [
        Role.EMPLOYEE,
        Role.SUPERVISOR,
        Role.SECURITY,
        Role.ADMIN,
        Role.EXECUTIVE,
    ],
)
def test_other_roles_do_not_grant_access_to_another_employee(
    role: Role,
) -> None:
    actor = ActorContext(
        actor_id=ACTOR_ID,
        employee_ref=OWN_EMPLOYEE_REF,
        roles=frozenset({role}),
    )

    assert can_read_history(actor, OTHER_EMPLOYEE_REF) is False


def test_hr_can_read_another_employee_history() -> None:
    actor = ActorContext(
        actor_id=ACTOR_ID,
        employee_ref=None,
        roles=frozenset({Role.HR}),
    )

    assert can_read_history(actor, OTHER_EMPLOYEE_REF) is True


def test_actor_without_employee_reference_or_hr_role_is_denied() -> None:
    actor = ActorContext(
        actor_id=ACTOR_ID,
        employee_ref=None,
        roles=frozenset(),
    )

    assert can_read_history(actor, OTHER_EMPLOYEE_REF) is False


def test_actor_id_does_not_grant_personal_history_access() -> None:
    actor = ActorContext(
        actor_id=OWN_EMPLOYEE_REF,
        employee_ref=None,
        roles=frozenset({Role.EMPLOYEE}),
    )

    assert can_read_history(actor, OWN_EMPLOYEE_REF) is False


def test_admin_can_read_own_history_without_access_to_others() -> None:
    actor = ActorContext(
        actor_id=ACTOR_ID,
        employee_ref=OWN_EMPLOYEE_REF,
        roles=frozenset({Role.ADMIN}),
    )

    assert can_read_history(actor, OWN_EMPLOYEE_REF) is True
    assert can_read_history(actor, OTHER_EMPLOYEE_REF) is False
