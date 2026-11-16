"""Tests for the base unit-of-work context manager."""

import pytest

from tmc_attendance.application.ports import UnitOfWork


class RecordingUnitOfWork(UnitOfWork):
    """Record lifecycle calls without implementing persistence."""

    def __init__(self) -> None:
        self.commit_calls = 0
        self.rollback_calls = 0

    def commit(self) -> None:
        self.commit_calls += 1

    def rollback(self) -> None:
        self.rollback_calls += 1


def test_context_returns_same_unit_of_work() -> None:
    uow = RecordingUnitOfWork()

    with uow as active:
        assert active is uow


def test_context_exit_requests_rollback_without_commit() -> None:
    uow = RecordingUnitOfWork()

    with uow:
        pass

    assert uow.commit_calls == 0
    assert uow.rollback_calls == 1


def test_context_propagates_exception_after_cleanup() -> None:
    uow = RecordingUnitOfWork()
    failure = RuntimeError("Transaction failed.")

    with pytest.raises(RuntimeError) as exc_info, uow:
        raise failure

    assert exc_info.value is failure
    assert uow.rollback_calls == 1


def test_context_requests_cleanup_after_explicit_commit() -> None:
    uow = RecordingUnitOfWork()

    with uow:
        uow.commit()

    assert uow.commit_calls == 1
    assert uow.rollback_calls == 1
