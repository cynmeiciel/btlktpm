"""Tests for ordered attendance batch ingestion."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from tests.factories import make_command, make_station
from tests.fakes import (
    FixedClock,
    InMemoryAttendanceStore,
    InMemoryUnitOfWork,
    InMemoryUnitOfWorkFactory,
    SequentialIdGenerator,
)
from tmc_attendance.application.dto import (
    BatchSummary,
    FieldError,
    InvalidItem,
)
from tmc_attendance.application.ingest_batch import (
    IngestAttendanceBatchUseCase,
)
from tmc_attendance.application.ingest_event import (
    IngestAttendanceEventUseCase,
)
from tmc_attendance.domain.dedup import ConflictKind, DeduplicationRule
from tmc_attendance.domain.model import Direction
from tmc_attendance.domain.policy import (
    EventValidationPolicy,
    IngestStatus,
    RejectionReason,
)

NOW = datetime(2026, 11, 3, 1, 0, tzinfo=UTC)


def make_batch_use_case(
    factory: InMemoryUnitOfWorkFactory,
) -> IngestAttendanceBatchUseCase:
    single = IngestAttendanceEventUseCase(
        factory,
        FixedClock(NOW),
        SequentialIdGenerator(),
        EventValidationPolicy(timedelta(seconds=300)),
        DeduplicationRule(),
    )
    return IngestAttendanceBatchUseCase(single)


def test_batch_accepts_distinct_events_in_input_order() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_batch_use_case(factory)
    commands = [make_command(event_id=UUID(int=value)) for value in [3, 1, 2]]

    batch = use_case.execute(commands, make_station())

    assert [result.index for result in batch.results] == [0, 1, 2]
    assert [result.event_id for result in batch.results] == [
        command.event_id for command in commands
    ]
    assert all(result.status is IngestStatus.ACCEPTED for result in batch.results)
    assert batch.summary == BatchSummary(accepted=3)
    assert store.count() == 3
    assert len(store.outbox) == 3
    assert factory.opened == 3
    assert factory.commits == 3


def test_mixed_batch_preserves_results_and_counts_each_status() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_batch_use_case(factory)
    original = make_command()
    changed = make_command(direction=Direction.OUT)
    error = FieldError(field="employeeRef", message="Field required.")
    invalid = InvalidItem(errors=(error,))

    batch = use_case.execute(
        [original, original, changed, invalid],
        make_station(),
    )

    assert [result.index for result in batch.results] == [0, 1, 2, 3]
    assert [result.status for result in batch.results] == [
        IngestStatus.ACCEPTED,
        IngestStatus.DUPLICATE,
        IngestStatus.CONFLICT,
        IngestStatus.REJECTED,
    ]
    assert batch.results[2].reason is ConflictKind.PAYLOAD_MISMATCH
    assert batch.results[3].reason is RejectionReason.INVALID_FORMAT
    assert batch.results[3].event_id is None
    assert batch.results[3].errors == (error,)
    assert batch.summary == BatchSummary(
        accepted=1,
        duplicate=1,
        conflict=1,
        rejected=1,
    )
    assert store.count() == 1
    assert len(store.outbox) == 1
    assert len(store.conflicts) == 1
    assert factory.opened == 3
    assert factory.commits == 3


def test_resending_batch_returns_duplicates_without_extra_records() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_batch_use_case(factory)
    commands = [make_command(event_id=UUID(int=value)) for value in range(1, 11)]
    first = use_case.execute(commands, make_station())

    resent = use_case.execute(commands, make_station())

    assert first.summary == BatchSummary(accepted=10)
    assert resent.summary == BatchSummary(duplicate=10)
    assert all(result.status is IngestStatus.DUPLICATE for result in resent.results)
    assert store.count() == 10
    assert len(store.outbox) == 10
    assert store.conflicts == []


@pytest.mark.parametrize("event_id", [None, UUID(int=99)])
def test_invalid_item_does_not_block_following_valid_event(
    event_id: UUID | None,
) -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_batch_use_case(factory)
    error = FieldError(field="employeeRef", message="Field required.")
    invalid = InvalidItem(errors=(error,), event_id=event_id)
    valid = make_command()

    batch = use_case.execute([invalid, valid], make_station())

    assert [result.status for result in batch.results] == [
        IngestStatus.REJECTED,
        IngestStatus.ACCEPTED,
    ]
    assert [result.index for result in batch.results] == [0, 1]
    assert batch.results[0].event_id == event_id
    assert batch.results[0].errors == (error,)
    assert batch.summary == BatchSummary(accepted=1, rejected=1)
    assert factory.opened == 1
    assert store.count() == 1


def test_rejected_command_does_not_block_following_valid_event() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_batch_use_case(factory)
    invalid = make_command(event_id=UUID(int=1), local_sequence=-1)
    valid = make_command(event_id=UUID(int=2))

    batch = use_case.execute([invalid, valid], make_station())

    assert [result.status for result in batch.results] == [
        IngestStatus.REJECTED,
        IngestStatus.ACCEPTED,
    ]
    assert batch.results[0].reason is RejectionReason.INVALID_FORMAT
    assert batch.summary == BatchSummary(accepted=1, rejected=1)
    assert factory.opened == 1
    assert valid.event_id in store.events
    assert invalid.event_id not in store.events


def test_all_invalid_items_are_counted_without_transactions() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_batch_use_case(factory)
    items = [
        InvalidItem(errors=(FieldError(field="eventId", message="Field required."),)),
        InvalidItem(errors=(FieldError(field="stationId", message="Field required."),)),
    ]

    batch = use_case.execute(items, make_station())

    assert batch.summary == BatchSummary(rejected=2)
    assert [result.index for result in batch.results] == [0, 1]
    assert factory.opened == 0
    assert store.count() == 0
    assert store.outbox == []


class FailSecondCommitFactory(InMemoryUnitOfWorkFactory):
    """Fail only the second transaction to simulate a mid-batch outage."""

    def __call__(self) -> InMemoryUnitOfWork:
        self.fail_on_commit = self.opened == 1
        return super().__call__()


def test_mid_batch_failure_preserves_commits_and_allows_safe_retry() -> None:
    store = InMemoryAttendanceStore()
    factory = FailSecondCommitFactory(store)
    use_case = make_batch_use_case(factory)
    commands = [make_command(event_id=UUID(int=value)) for value in [1, 2, 3]]

    with pytest.raises(RuntimeError, match="Simulated commit failure"):
        use_case.execute(commands, make_station())

    assert set(store.events) == {commands[0].event_id}
    assert len(store.outbox) == 1
    assert factory.opened == 2
    assert factory.commits == 1
    assert factory.rollbacks == 1

    retried = use_case.execute(commands, make_station())

    assert [result.status for result in retried.results] == [
        IngestStatus.DUPLICATE,
        IngestStatus.ACCEPTED,
        IngestStatus.ACCEPTED,
    ]
    assert retried.summary == BatchSummary(accepted=2, duplicate=1)
    assert store.count() == 3
    assert len(store.outbox) == 3
    assert factory.commits == 4
    assert factory.rollbacks == 1
