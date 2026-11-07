"""In-memory implementations of the ports, for unit and API tests.

Each fake inherits the real port, so a wrong call is a type error, not a silent pass
(docs/05-testing-strategy.md §2). The full list arrives with T2.2.
"""

from tmc_attendance.application.ports import HealthProbe


class FakeHealthProbe(HealthProbe):
    def __init__(self, *, ready: bool = True) -> None:
        self.ready = ready

    def is_ready(self) -> bool:
        return self.ready
