"""Application use case for ordered attendance batch ingestion."""

from collections import Counter
from collections.abc import Sequence
from dataclasses import replace

from tmc_attendance.application.dto import (
    AuthenticatedStation,
    BatchResult,
    BatchSummary,
    IngestEventCommand,
    IngestResult,
    InvalidItem,
)
from tmc_attendance.application.ingest_event import (
    IngestAttendanceEventUseCase,
)
from tmc_attendance.domain.policy import IngestStatus, RejectionReason


class IngestAttendanceBatchUseCase:
    """Process each batch item independently and preserve input order."""

    def __init__(self, single: IngestAttendanceEventUseCase) -> None:
        self._single = single

    def execute(
        self,
        items: Sequence[IngestEventCommand | InvalidItem],
        station: AuthenticatedStation,
    ) -> BatchResult:
        results: list[IngestResult] = []

        for index, item in enumerate(items):
            if isinstance(item, InvalidItem):
                result = IngestResult(
                    event_id=item.event_id,
                    status=IngestStatus.REJECTED,
                    reason=RejectionReason.INVALID_FORMAT,
                    errors=item.errors,
                )
            else:
                result = self._single.execute(item, station)

            results.append(replace(result, index=index))

        counts = Counter(result.status for result in results)

        return BatchResult(
            results=tuple(results),
            summary=BatchSummary(
                accepted=counts[IngestStatus.ACCEPTED],
                duplicate=counts[IngestStatus.DUPLICATE],
                conflict=counts[IngestStatus.CONFLICT],
                rejected=counts[IngestStatus.REJECTED],
            ),
        )
