"""Pydantic request schemas for the attendance ingest API."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from tmc_attendance.domain.model import Direction, EvidenceLevel


class EventIn(BaseModel):
    """One event in a batch; extra fields are ignored for tolerant reading."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )

    event_id: UUID
    attempt_id: UUID
    employee_ref: UUID
    station_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    direction: Direction
    occurred_at: datetime
    local_sequence: int = Field(ge=0)
    evidence_level: EvidenceLevel
    schema_version: int

    @field_validator("occurred_at")
    @classmethod
    def require_timezone_offset(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Datetime must include a timezone offset")
        return value


class BatchIn(BaseModel):
    """Envelope model; event items are validated independently by the controller."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )

    station_id: str
    events: list[dict[str, Any]] = Field(min_length=1)
