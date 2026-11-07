"""Smoke test for the DB test infrastructure (T0.5): each role can log in."""

from sqlalchemy import Engine, text


def test_app_role_can_query_database(app_engine: Engine) -> None:
    with app_engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar_one() == 1


def test_each_fixture_connects_as_its_own_role(
    owner_engine: Engine, app_engine: Engine, reader_engine: Engine
) -> None:
    expected = {
        "s3_attendance_owner": owner_engine,
        "s3_attendance_app": app_engine,
        "s4_reporting_reader": reader_engine,
    }
    for role, engine in expected.items():
        with engine.connect() as conn:
            assert conn.execute(text("SELECT current_user")).scalar_one() == role
