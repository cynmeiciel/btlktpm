"""Tests for duplicate and conflict classification."""

from tests.factories import make_event
from tmc_attendance.domain.dedup import (
    DedupDecision,
    DeduplicationRule,
    compute_payload_hash,
)
from tmc_attendance.domain.model import Direction
from tmc_attendance.domain.values import PayloadHash


def test_same_hash_is_duplicate() -> None:
    payload_hash = PayloadHash("a" * 64)

    decision = DeduplicationRule().decide(payload_hash, payload_hash)

    assert decision is DedupDecision.DUPLICATE


def test_different_hash_is_conflict() -> None:
    incoming = PayloadHash("a" * 64)
    existing = PayloadHash("b" * 64)

    decision = DeduplicationRule().decide(incoming, existing)

    assert decision is DedupDecision.CONFLICT


def test_same_event_id_with_changed_content_is_conflict() -> None:
    original = make_event()
    changed = make_event(direction=Direction.OUT)

    decision = DeduplicationRule().decide(
        incoming=compute_payload_hash(changed),
        existing=compute_payload_hash(original),
    )

    assert original.event_id == changed.event_id
    assert decision is DedupDecision.CONFLICT
