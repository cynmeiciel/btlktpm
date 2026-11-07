"""Behavioural contract shared by every ``AttendanceWriter`` implementation (LSP evidence).

Subclass it once per implementation; the subclass location decides the marker:

- ``tests/unit/application/test_in_memory_writer_contract.py``  — fake (T2.2)
- ``tests/integration/persistence/test_postgres_writer_contract.py`` — Postgres (T3.3)

This file does not start with ``test_`` so pytest never collects the base class directly.
See docs/05-testing-strategy.md §2.

Skeleton from T0.5: bodies are skipped until the port (T2.1) and the fake (T2.2) exist.
When filling them in, change ``object`` to ``UnitOfWorkFactory`` from
``tmc_attendance.application.ports``.
"""

import pytest

PENDING = "pending T2.2: needs UnitOfWorkFactory (T2.1) and InMemoryUnitOfWorkFactory (T2.2)"


class AttendanceWriterContract:
    @pytest.fixture
    def uow_factory(self) -> object:
        raise NotImplementedError("subclass must provide a UnitOfWorkFactory")

    def test_first_insert_returns_inserted(self, uow_factory: object) -> None:
        pytest.skip(PENDING)

    def test_same_event_id_returns_event_id_exists_with_hash(self, uow_factory: object) -> None:
        pytest.skip(PENDING)

    def test_nothing_visible_without_commit(self, uow_factory: object) -> None:
        pytest.skip(PENDING)
