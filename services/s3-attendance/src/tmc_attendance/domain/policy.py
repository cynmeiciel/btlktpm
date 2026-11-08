"""Ingestion statuses and event rejection reasons."""

from enum import StrEnum


class IngestStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    REJECTED = "REJECTED"


class RejectionReason(StrEnum):
    INVALID_FORMAT = "INVALID_FORMAT"
    UNSUPPORTED_SCHEMA_VERSION = "UNSUPPORTED_SCHEMA_VERSION"
    CLOCK_SKEW = "CLOCK_SKEW"
    STATION_MISMATCH = "STATION_MISMATCH"
