"""Conflict types for attendance event deduplication."""

from enum import StrEnum


class ConflictKind(StrEnum):
    PAYLOAD_MISMATCH = "PAYLOAD_MISMATCH"
