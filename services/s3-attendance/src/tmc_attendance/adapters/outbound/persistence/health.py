"""PostgreSQL implementation of the ``HealthProbe`` port."""

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from tmc_attendance.application.ports import HealthProbe


class PostgresHealthProbe(HealthProbe):
    """Ready when a trivial query succeeds on the application's engine.

    The engine must be created with a connect timeout (see ``bootstrap/container.py``)
    so that an unreachable database yields ``False`` quickly instead of hanging.
    """

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def is_ready(self) -> bool:
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return False
        return True
