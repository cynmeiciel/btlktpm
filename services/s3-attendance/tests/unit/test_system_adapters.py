"""SystemClock and Uuid4Generator honour the same port contracts as the test fakes."""

from datetime import UTC, datetime, timedelta

import pytest

from tests.fakes import FixedClock, SequentialIdGenerator
from tmc_attendance.adapters.outbound.clock import SystemClock
from tmc_attendance.adapters.outbound.ids import Uuid4Generator
from tmc_attendance.application.ports import Clock, IdGenerator


@pytest.mark.parametrize(
    "clock",
    [SystemClock(), FixedClock(datetime(2026, 11, 3, 7, 58, tzinfo=UTC))],
    ids=["system", "fixed"],
)
def test_clock_returns_aware_utc_datetime(clock: Clock) -> None:
    now = clock.now()

    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_system_clock_follows_real_time() -> None:
    before = datetime.now(UTC)
    now = SystemClock().now()
    after = datetime.now(UTC)

    assert before <= now <= after


@pytest.mark.parametrize(
    "ids",
    [Uuid4Generator(), SequentialIdGenerator()],
    ids=["uuid4", "sequential"],
)
def test_id_generator_returns_distinct_ids(ids: IdGenerator) -> None:
    generated = {ids.new_id() for _ in range(100)}

    assert len(generated) == 100


def test_uuid4_generator_returns_version_4() -> None:
    assert Uuid4Generator().new_id().version == 4
