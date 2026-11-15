"""FastAPI application factory."""

from fastapi import FastAPI

from tmc_attendance.adapters.inbound.http import health
from tmc_attendance.adapters.inbound.http.dependencies import ApiDependencies
from tmc_attendance.adapters.inbound.http.errors import register_exception_handlers


def create_app(deps: ApiDependencies) -> FastAPI:
    """Build the HTTP application around already-wired dependencies."""
    app = FastAPI(title="TMC S3 Attendance", version="0.1.0")
    app.state.api_dependencies = deps
    register_exception_handlers(app)
    app.include_router(health.router)
    return app
