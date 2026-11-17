import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError


def test_s4_reader_can_read_versioned_view(reader_engine: Engine) -> None:
    with reader_engine.connect() as conn:
        conn.execute(
            text("SELECT event_id FROM attendance.v1_attendance_event LIMIT 1")
        ).all()


def test_s4_reader_cannot_read_base_table(reader_engine: Engine) -> None:
    with reader_engine.connect() as conn, pytest.raises(DBAPIError) as exc_info:
        conn.execute(text("SELECT event_id FROM attendance.attendance_event LIMIT 1"))

    assert getattr(exc_info.value.orig, "sqlstate", None) == "42501"
