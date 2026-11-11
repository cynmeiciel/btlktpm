"""Tests for transactional conflict persistence."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from tests.factories import make_event
from tests.fakes import (
    InMemoryAttendanceStore,
    InMemoryUnitOfWorkFactory,
    StoredAttendanceEvent,
)
from tmc_attendance.application.dto import EventConflict
from tmc_attendance.domain.dedup import (
    ConflictKind,
    compute_payload_hash,
)
from tmc_attendance.domain.model import Direction

NOW = datetime(2026, 11, 3, 1, 0, tzinfo=UTC)


@pytest.mark.parametrize("commit", [True, False])
def test_conflict_is_persisted_only_after_commit(commit: bool) -> None:
    store = InMemoryAttendanceStore()
    original = make_event()
    stored = StoredAttendanceEvent(
        event=original,
        payload_hash=compute_payload_hash(original),
        received_at=NOW,
    )
    store.events[original.event_id] = stored

    changed = make_event(direction=Direction.OUT)
    conflict = EventConflict(
        conflict_id=UUID(int=100),
        event_id=original.event_id,
        station_id=original.station_id,
        kind=ConflictKind.PAYLOAD_MISMATCH,
        incoming_payload={"direction": "OUT"},
        incoming_hash=compute_payload_hash(changed),
        detected_at=NOW,
    )
    factory = InMemoryUnitOfWorkFactory(store)

    with factory() as uow:
        uow.attendance.record_conflict(conflict)
        assert store.conflicts == []

        if commit:
            uow.commit()

    assert store.conflicts == ([conflict] if commit else [])
    assert store.events[original.event_id] == stored
    assert store.count() == 1
