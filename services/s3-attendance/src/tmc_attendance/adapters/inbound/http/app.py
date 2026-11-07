"""FastAPI application factory."""

from fastapi import FastAPI

from tmc_attendance.adapters.inbound.http import health
from tmc_attendance.adapters.inbound.http.dependencies import ApiDependencies


def create_app(deps: ApiDependencies) -> FastAPI:
    """Build the HTTP application around already-wired dependencies.

    Error handlers are added in T4.1; ingest and history routes in T4.3 and T5.2.
    """
    app = FastAPI(title="TMC S3 Attendance", version="0.1.0")
    app.state.api_dependencies = deps
    app.include_router(health.router)
    return app
