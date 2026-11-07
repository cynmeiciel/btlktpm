import pytest


@pytest.fixture(autouse=True)
def _clean_attendance_schema(clean_db: None) -> None:
    """Every integration test starts from empty ``attendance`` tables (docs/04-database.md §7)."""
