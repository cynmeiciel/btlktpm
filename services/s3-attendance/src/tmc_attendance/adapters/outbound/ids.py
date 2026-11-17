"""Random UUID adapter for the ``IdGenerator`` port."""

from uuid import UUID, uuid4

from tmc_attendance.application.ports import IdGenerator


class Uuid4Generator(IdGenerator):
    """Generate random version-4 UUIDs for outbox messages and conflict records.

    Never used for ``eventId``: stations generate those (docs/00-tong-quan.md §7, rule 8).
    """

    def new_id(self) -> UUID:
        return uuid4()
