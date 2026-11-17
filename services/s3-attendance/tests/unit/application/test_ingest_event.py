"""Tests for single-event attendance ingestion."""

from datetime import UTC, datetime, timedelta

import pytest

from tests.factories import make_command, make_station
from tests.fakes import (
    FixedClock,
    InMemoryAttendanceStore,
    InMemoryUnitOfWorkFactory,
    SequentialIdGenerator,
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


def make_use_case(
    factory: InMemoryUnitOfWorkFactory,
) -> IngestAttendanceEventUseCase:
    return IngestAttendanceEventUseCase(
        factory,
        FixedClock(NOW),
        SequentialIdGenerator(),
        EventValidationPolicy(timedelta(seconds=300)),
        DeduplicationRule(),
    )


def test_new_event_is_accepted_with_committed_outbox() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_use_case(factory)
    command = make_command()

    result = use_case.execute(command, make_station())

    assert result.status is IngestStatus.ACCEPTED
    assert result.event_id == command.event_id
    assert store.count() == 1
    assert store.events[command.event_id].received_at == NOW
    assert len(store.outbox) == 1
    assert store.outbox[0].aggregate_id == command.event_id
    assert store.outbox[0].message_type == "AttendanceEventAccepted.v1"
    assert factory.commits == 1


def test_resending_same_event_does_not_add_event_or_outbox() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_use_case(factory)
    command = make_command()
    use_case.execute(command, make_station())

    result = use_case.execute(command, make_station())

    assert result.status is IngestStatus.DUPLICATE
    assert store.count() == 1
    assert len(store.outbox) == 1
    assert store.conflicts == []
    assert factory.commits == 2


def test_changed_payload_creates_conflict_without_overwriting_event() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_use_case(factory)
    original = make_command()
    use_case.execute(original, make_station())
    stored_original = store.events[original.event_id]
    changed = make_command(direction=Direction.OUT)

    result = use_case.execute(changed, make_station())

    assert result.status is IngestStatus.CONFLICT
    assert result.reason is ConflictKind.PAYLOAD_MISMATCH
    assert store.events[original.event_id] == stored_original
    assert store.count() == 1
    assert len(store.outbox) == 1
    assert len(store.conflicts) == 1
    assert store.conflicts[0].incoming_payload["direction"] == "OUT"


@pytest.mark.parametrize(
    ("overrides", "expected_reason", "error_field"),
    [
        (
            {"local_sequence": -1},
            RejectionReason.INVALID_FORMAT,
            "localSequence",
        ),
        (
            {"schema_version": 2},
            RejectionReason.UNSUPPORTED_SCHEMA_VERSION,
            None,
        ),
        (
            {"station_id": "BAD STATION"},
            RejectionReason.INVALID_FORMAT,
            "stationId",
        ),
        (
            {"occurred_at": NOW.replace(tzinfo=None)},
            RejectionReason.INVALID_FORMAT,
            "occurredAt",
        ),
    ],
)
def test_invalid_event_is_rejected_without_opening_transaction(
    overrides: dict[str, object],
    expected_reason: RejectionReason,
    error_field: str | None,
) -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_use_case(factory)

    result = use_case.execute(make_command(**overrides), make_station())

    assert result.status is IngestStatus.REJECTED
    assert result.reason is expected_reason
    assert factory.opened == 0
    assert store.count() == 0
    assert store.outbox == []

    if error_field is None:
        assert result.errors == ()
    else:
        assert len(result.errors) == 1
        assert result.errors[0].field == error_field


def test_station_mismatch_is_rejected_without_opening_transaction() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_use_case(factory)

    result = use_case.execute(
        make_command(),
        make_station("LA-G02-OUT"),
    )

    assert result.status is IngestStatus.REJECTED
    assert result.reason is RejectionReason.STATION_MISMATCH
    assert factory.opened == 0


def test_future_event_is_rejected_without_opening_transaction() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_use_case(factory)
    command = make_command(
        occurred_at=NOW + timedelta(seconds=301),
    )

    result = use_case.execute(command, make_station())

    assert result.status is IngestStatus.REJECTED
    assert result.reason is RejectionReason.CLOCK_SKEW
    assert factory.opened == 0


def test_old_event_is_accepted_after_delayed_synchronization() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_use_case(factory)
    command = make_command(
        occurred_at=NOW - timedelta(days=30),
    )

    result = use_case.execute(command, make_station())

    assert result.status is IngestStatus.ACCEPTED
    assert store.count() == 1
    assert factory.commits == 1


@pytest.mark.parametrize(
    ("failure_flag", "message"),
    [
        ("fail_on_commit", "Simulated commit failure"),
        ("fail_on_outbox_add", "Simulated outbox failure"),
    ],
)
def test_persistence_failure_propagates_without_partial_records(
    failure_flag: str,
    message: str,
) -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    setattr(factory, failure_flag, True)
    use_case = make_use_case(factory)

    with pytest.raises(RuntimeError, match=message):
        use_case.execute(make_command(), make_station())

    assert store.count() == 0
    assert store.outbox == []
    assert store.conflicts == []
    assert factory.commits == 0
    assert factory.rollbacks == 1


@pytest.mark.parametrize("direction", [Direction.IN, Direction.OUT])
def test_failed_commit_preserves_previously_committed_event(
    direction: Direction,
) -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_use_case(factory)
    original = make_command()
    use_case.execute(original, make_station())
    stored_original = store.events[original.event_id]

    factory.fail_on_commit = True
    command = make_command(direction=direction)

    with pytest.raises(RuntimeError, match="Simulated commit failure"):
        use_case.execute(command, make_station())

    assert store.events[original.event_id] == stored_original
    assert store.count() == 1
    assert len(store.outbox) == 1
    assert store.conflicts == []
    assert factory.commits == 1
    assert factory.rollbacks == 1


def test_accepted_message_contains_only_the_public_event_fields() -> None:
    store = InMemoryAttendanceStore()
    factory = InMemoryUnitOfWorkFactory(store)
    use_case = make_use_case(factory)
    command = make_command()

    use_case.execute(command, make_station())

    message = store.outbox[0]
    assert message.payload == {
        "eventId": str(command.event_id),
        "employeeRef": str(command.employee_ref),
        "stationId": command.station_id,
        "direction": "IN",
        "occurredAt": "2026-11-03T00:58:12.345000+00:00",
        "evidenceLevel": "CONTROLLER_CONFIRMED",
        "receivedAt": "2026-11-03T01:00:00.000000+00:00",
    }
    assert message.occurred_at == NOW
