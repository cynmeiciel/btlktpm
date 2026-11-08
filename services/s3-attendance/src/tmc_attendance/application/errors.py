"""Exceptions raised when application queries cannot be served."""


class AccessDenied(Exception):  # noqa: N818 - Keep the specified application name.
    """Indicate that an actor cannot access the requested resource."""


class InvalidQuery(Exception):  # noqa: N818 - Keep the specified application name.
    """Indicate that query parameters violate application constraints."""
