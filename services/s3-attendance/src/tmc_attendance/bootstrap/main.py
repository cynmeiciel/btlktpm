"""ASGI entry point: ``uvicorn tmc_attendance.bootstrap.main:app``. No logic here."""

from tmc_attendance.adapters.inbound.http.app import create_app
from tmc_attendance.bootstrap.config import Settings
from tmc_attendance.bootstrap.container import build_api_dependencies

app = create_app(build_api_dependencies(Settings()))
