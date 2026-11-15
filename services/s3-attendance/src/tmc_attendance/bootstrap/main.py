"""ASGI entry point: ``uvicorn tmc_attendance.bootstrap.main:app``. No logic here."""

import logging

from tmc_attendance.adapters.inbound.http.app import create_app
from tmc_attendance.bootstrap.config import Settings
from tmc_attendance.bootstrap.container import build_api_dependencies

settings = Settings()
logging.basicConfig(level=settings.log_level.upper())
app = create_app(build_api_dependencies(settings))
