"""Verify database least-privilege rules for runtime roles."""

import pytest
from psycopg.errors import InsufficientPrivilege
from sqlalchemy import Engine, text
from sqlalchemy.exc import DBAPIError


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE attendance.attendance_event SET station_id = 'changed' WHERE false",
        "DELETE FROM attendance.attendance_event WHERE false",
    ],
)
def test_app_role_cannot_update_or_delete_events(
    app_engine: Engine,
    statement: str,
) -> None:
    with pytest.raises(DBAPIError) as exc_info, app_engine.connect() as connection:
        connection.execute(text(statement))

    assert isinstance(exc_info.value.orig, InsufficientPrivilege)


def test_reporting_reader_can_read_view_but_not_event_table(
    reader_engine: Engine,
) -> None:
    with reader_engine.connect() as connection:
        connection.execute(text("SELECT * FROM attendance.v1_attendance_event")).all()

    with pytest.raises(DBAPIError) as exc_info, reader_engine.connect() as connection:
        connection.execute(text("SELECT * FROM attendance.attendance_event")).all()

    assert isinstance(exc_info.value.orig, InsufficientPrivilege)
