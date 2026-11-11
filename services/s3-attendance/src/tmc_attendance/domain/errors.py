"""Exceptions raised when domain invariants are violated."""


class DomainError(Exception):
    """Base exception for domain errors."""


class InvalidEvent(DomainError):  # noqa: N818 - Keep the specified domain name.
    """Describe an invalid event field without exposing its input value."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")
