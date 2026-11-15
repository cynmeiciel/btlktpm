"""Data contracts exchanged by application use cases."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from tmc_attendance.domain.dedup import ConflictKind
from tmc_attendance.domain.model import Direction, EvidenceLevel
from tmc_attendance.domain.policy import IngestStatus, RejectionReason
from tmc_attendance.domain.values import PayloadHash, StationId


@dataclass(frozen=True, slots=True)
class IngestEventCommand:
    """Carry parsed event data into the ingestion use case."""

    event_id: UUID
    attempt_id: UUID
    employee_ref: UUID
    station_id: StationId
    direction: Direction
    occurred_at: datetime
    local_sequence: int
    evidence_level: EvidenceLevel
    schema_version: int
@dataclass(frozen=True, slots=True)
class AuthenticatedStation:
    """Identify the station established by device authentication."""

    station_id: StationId


@dataclass(frozen=True, slots=True)
class FieldError:
    """Describe an invalid field without exposing its input value."""

    field: str
    message: str


@dataclass(frozen=True, slots=True)
class InvalidItem:
    """Represent an item that the inbound adapter could not parse."""

    errors: tuple[FieldError, ...]
    event_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class IngestResult:
    """Describe the outcome of processing one attendance event."""

    event_id: UUID | None
    status: IngestStatus
    reason: RejectionReason | ConflictKind | None = None
    errors: tuple[FieldError, ...] = ()
    index: int | None = None


@dataclass(frozen=True, slots=True)
class BatchSummary:
    """Count ingestion outcomes within a batch."""

    accepted: int = 0
    duplicate: int = 0
    conflict: int = 0
    rejected: int = 0


@dataclass(frozen=True, slots=True)
class BatchResult:
    """Preserve ordered item outcomes and their summary."""

    results: tuple[IngestResult, ...]
    summary: BatchSummary


@dataclass(frozen=True, slots=True)
class EventConflict:
    """Preserve evidence of a conflicting event submission."""

    conflict_id: UUID
    event_id: UUID
    station_id: StationId
    kind: ConflictKind
    incoming_payload: Mapping[str, object]
    incoming_hash: PayloadHash
    detected_at: datetime


@dataclass(frozen=True, slots=True)
class OutboxMessage:
    """Represent a message persisted alongside a business transaction."""

    message_id: UUID
    aggregate_id: UUID
    message_type: str
    payload: Mapping[str, object]
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class HistoryQuery:
    """Describe the requested employee history range and page."""

    employee_ref: UUID
    occurred_from: datetime
    occurred_to: datetime
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class AttendanceEventView:
    """Expose attendance event fields required by history consumers."""

    event_id: UUID
    station_id: StationId
    direction: Direction
    occurred_at: datetime
    received_at: datetime
    evidence_level: EvidenceLevel


@dataclass(frozen=True, slots=True)
class HistoryPage:
    """Return an ordered page of attendance history."""

    items: tuple[AttendanceEventView, ...]
    has_more: bool
