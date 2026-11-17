"""Canonical payloads and conflict types for attendance events."""

import hashlib
import hmac
import json
from datetime import UTC
from enum import StrEnum

from tmc_attendance.domain.model import AttendanceEvent
from tmc_attendance.domain.values import PayloadHash


class ConflictKind(StrEnum):
    PAYLOAD_MISMATCH = "PAYLOAD_MISMATCH"


def canonical_payload(event: AttendanceEvent) -> bytes:
    """Serialize the standard event fields using a stable representation."""
    payload: dict[str, object] = {
        "eventId": str(event.event_id),
        "attemptId": str(event.attempt_id),
        "employeeRef": str(event.employee_ref),
        "stationId": event.station_id,
        "direction": event.direction.value,
        "occurredAt": event.occurred_at.astimezone(UTC).isoformat(timespec="microseconds"),
        "localSequence": event.local_sequence,
        "evidenceLevel": event.evidence_level.value,
        "schemaVersion": event.schema_version,
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def compute_payload_hash(event: AttendanceEvent) -> PayloadHash:
    """Return the SHA-256 digest of the canonical event payload."""
    return PayloadHash(hashlib.sha256(canonical_payload(event)).hexdigest())


class DedupDecision(StrEnum):
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"


class DeduplicationRule:
    """Classify submissions whose event identifier already exists."""

    def decide(
        self,
        incoming: PayloadHash,
        existing: PayloadHash,
    ) -> DedupDecision:
        """Compare the incoming payload hash with the stored hash."""
        if hmac.compare_digest(incoming, existing):
            return DedupDecision.DUPLICATE

        return DedupDecision.CONFLICT
