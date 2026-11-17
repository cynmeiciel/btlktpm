"""Tests for attendance timestamp validation."""

from datetime import UTC, datetime, timedelta

import pytest

from tests.factories import make_event
from tmc_attendance.domain.policy import (
    EventValidationPolicy,
    RejectionReason,
)

RECEIVED_AT = datetime(2026, 11, 3, 1, 0, tzinfo=UTC)


@pytest.mark.parametrize("seconds", [0, 299, 300])
def test_timestamp_within_future_limit_is_accepted(seconds: int) -> None:
    policy = EventValidationPolicy(timedelta(seconds=300))
    event = make_event(
        occurred_at=RECEIVED_AT + timedelta(seconds=seconds),
    )

    reason = policy.check(event, RECEIVED_AT)

    assert reason is None


def test_timestamp_beyond_future_limit_is_rejected() -> None:
    policy = EventValidationPolicy(timedelta(seconds=300))
    event = make_event(
        occurred_at=RECEIVED_AT + timedelta(seconds=301),
    )

    reason = policy.check(event, RECEIVED_AT)

    assert reason is RejectionReason.CLOCK_SKEW


def test_old_event_is_accepted_for_delayed_synchronization() -> None:
    policy = EventValidationPolicy(timedelta(seconds=300))
    event = make_event(
        occurred_at=RECEIVED_AT - timedelta(days=30),
    )

    reason = policy.check(event, RECEIVED_AT)

    assert reason is None


def test_policy_uses_the_configured_future_limit() -> None:
    policy = EventValidationPolicy(timedelta(seconds=60))
    event = make_event(
        occurred_at=RECEIVED_AT + timedelta(seconds=61),
    )

    reason = policy.check(event, RECEIVED_AT)

    assert reason is RejectionReason.CLOCK_SKEW
