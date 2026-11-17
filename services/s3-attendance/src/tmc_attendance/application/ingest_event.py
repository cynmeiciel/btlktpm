"""Application use case for ingesting one attendance event."""

import json
from datetime import UTC, datetime

from tmc_attendance.application.dto import (
    AuthenticatedStation,
    EventConflict,
    FieldError,
    IngestEventCommand,
    IngestResult,
    OutboxMessage,
)
from tmc_attendance.application.ports import (
    Clock,
    IdGenerator,
    Inserted,
    UnitOfWork,
    UnitOfWorkFactory,
)
from tmc_attendance.domain.dedup import (
    ConflictKind,
    DedupDecision,
    DeduplicationRule,
    canonical_payload,
    compute_payload_hash,
)
from tmc_attendance.domain.errors import InvalidEvent
from tmc_attendance.domain.model import AttendanceEvent
from tmc_attendance.domain.policy import (
    EventValidationPolicy,
    IngestStatus,
    RejectionReason,
)
from tmc_attendance.domain.values import PayloadHash


class IngestAttendanceEventUseCase:
    """Validate and persist one event using application ports."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        clock: Clock,
        ids: IdGenerator,
        policy: EventValidationPolicy,
        rule: DeduplicationRule,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._ids = ids
        self._policy = policy
        self._rule = rule

    def execute(
        self,
        cmd: IngestEventCommand,
        station: AuthenticatedStation,
    ) -> IngestResult:
        received_at = self._clock.now()

        try:
            event = self._build_event(cmd)
        except InvalidEvent as error:
            unsupported = error.field == "schemaVersion"
            return IngestResult(
                event_id=cmd.event_id,
                status=IngestStatus.REJECTED,
                reason=(
                    RejectionReason.UNSUPPORTED_SCHEMA_VERSION
                    if unsupported
                    else RejectionReason.INVALID_FORMAT
                ),
                errors=(
                    () if unsupported else (FieldError(field=error.field, message=error.message),)
                ),
            )

        if event.station_id != station.station_id:
            return IngestResult(
                event_id=event.event_id,
                status=IngestStatus.REJECTED,
                reason=RejectionReason.STATION_MISMATCH,
            )

        reason = self._policy.check(event, received_at)
        if reason is not None:
            return IngestResult(
                event_id=event.event_id,
                status=IngestStatus.REJECTED,
                reason=reason,
            )

        return self._persist(event, received_at)

    @staticmethod
    def _build_event(cmd: IngestEventCommand) -> AttendanceEvent:
        return AttendanceEvent(
            event_id=cmd.event_id,
            attempt_id=cmd.attempt_id,
            employee_ref=cmd.employee_ref,
            station_id=cmd.station_id,
            direction=cmd.direction,
            occurred_at=cmd.occurred_at,
            local_sequence=cmd.local_sequence,
            evidence_level=cmd.evidence_level,
            schema_version=cmd.schema_version,
        )

    def _persist(
        self,
        event: AttendanceEvent,
        received_at: datetime,
    ) -> IngestResult:
        payload_hash = compute_payload_hash(event)

        with self._uow_factory() as uow:
            outcome = uow.attendance.insert_if_absent(event, payload_hash, received_at)

            if isinstance(outcome, Inserted):
                uow.outbox.add(self._outbox_message(event, received_at))
                result = IngestResult(
                    event_id=event.event_id,
                    status=IngestStatus.ACCEPTED,
                )
            elif self._rule.decide(payload_hash, outcome.existing_hash) is DedupDecision.DUPLICATE:
                result = IngestResult(
                    event_id=event.event_id,
                    status=IngestStatus.DUPLICATE,
                )
            else:
                self._record_conflict(uow, event, payload_hash, received_at)
                result = IngestResult(
                    event_id=event.event_id,
                    status=IngestStatus.CONFLICT,
                    reason=ConflictKind.PAYLOAD_MISMATCH,
                )

            uow.commit()

        return result

    def _outbox_message(
        self,
        event: AttendanceEvent,
        received_at: datetime,
    ) -> OutboxMessage:
        return OutboxMessage(
            message_id=self._ids.new_id(),
            aggregate_id=event.event_id,
            message_type="AttendanceEventAccepted.v1",
            payload={
                "eventId": str(event.event_id),
                "employeeRef": str(event.employee_ref),
                "stationId": event.station_id,
                "direction": event.direction.value,
                "occurredAt": event.occurred_at.astimezone(UTC).isoformat(timespec="microseconds"),
                "evidenceLevel": event.evidence_level.value,
                "receivedAt": received_at.astimezone(UTC).isoformat(timespec="microseconds"),
            },
            occurred_at=received_at,
        )

    def _record_conflict(
        self,
        uow: UnitOfWork,
        event: AttendanceEvent,
        payload_hash: PayloadHash,
        received_at: datetime,
    ) -> None:
        payload: dict[str, object] = json.loads(canonical_payload(event))
        conflict = EventConflict(
            conflict_id=self._ids.new_id(),
            event_id=event.event_id,
            station_id=event.station_id,
            kind=ConflictKind.PAYLOAD_MISMATCH,
            incoming_payload=payload,
            incoming_hash=payload_hash,
            detected_at=received_at,
        )
        uow.attendance.record_conflict(conflict)
