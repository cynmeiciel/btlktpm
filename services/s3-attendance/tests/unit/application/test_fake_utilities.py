"""Tests for deterministic clock and identifier utilities."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from tests.fakes import FixedClock, SequentialIdGenerator

NOW = datetime(2026, 11, 3, 1, 0, tzinfo=UTC)


def test_fixed_clock_keeps_time_until_advanced() -> None:
    clock = FixedClock(NOW)

    assert clock.now() == NOW
    assert clock.now() == NOW


def test_clock_can_advance_without_waiting() -> None:
    clock = FixedClock(NOW)

    clock.advance(timedelta(seconds=301))

    assert clock.now() == NOW + timedelta(seconds=301)


def test_clock_normalizes_input_to_utc() -> None:
    local_timezone = timezone(timedelta(hours=7))
    local_time = datetime(2026, 11, 3, 8, 0, tzinfo=local_timezone)
    clock = FixedClock(local_time)

    assert clock.now() == NOW
    assert clock.now().tzinfo is UTC


def test_clock_rejects_time_without_timezone() -> None:
    naive_time = NOW.replace(tzinfo=None)

    with pytest.raises(ValueError, match="timezone offset"):
        FixedClock(naive_time)


def test_generator_returns_distinct_ids_in_sequence() -> None:
    generator = SequentialIdGenerator()

    identifiers = [generator.new_id() for _ in range(3)]

    assert identifiers == [
        UUID(int=1),
        UUID(int=2),
        UUID(int=3),
    ]


def test_new_generator_restarts_the_same_sequence() -> None:
    first = SequentialIdGenerator()
    second = SequentialIdGenerator()

    assert first.new_id() == second.new_id() == UUID(int=1)
    assert first.new_id() == second.new_id() == UUID(int=2)
