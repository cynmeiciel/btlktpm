"""HTTP exception handlers that keep request data and infrastructure details private."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register the API's sanitized validation and database error responses."""

    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(OperationalError, handle_database_error)


async def handle_validation_error(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):
        raise TypeError("Validation handler received an unexpected exception")
    errors = [
        {
            "field": field_name(error["loc"]),
            "message": safe_validation_message(error["type"]),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "errors": errors},
    )


async def handle_database_error(_request: Request, _exc: Exception) -> JSONResponse:
    logger.warning("Database operation failed; returning service unavailable")
    return JSONResponse(status_code=503, content={"detail": "Service unavailable"})


def field_name(location: tuple[str | int, ...]) -> str:
    parts = [str(part) for part in location if part not in {"body", "query", "path", "header"}]
    return ".".join(parts) or "request"


def safe_validation_message(error_type: str) -> str:
    if error_type.startswith("datetime_"):
        return "Input should be a valid datetime"
    messages = {
        "missing": "Field required",
        "int_parsing": "Input should be a valid integer",
        "float_parsing": "Input should be a valid number",
        "string_type": "Input should be a valid string",
        "list_type": "Input should be a valid list",
        "dict_type": "Input should be a valid object",
        "bool_parsing": "Input should be a valid boolean",
        "uuid_parsing": "Input should be a valid UUID",
        "datetime_parsing": "Input should be a valid datetime",
        "json_invalid": "Invalid JSON",
        "too_short": "Value has too few items",
        "too_long": "Value has too many items",
        "greater_than_equal": "Value is below the allowed minimum",
        "less_than_equal": "Value is above the allowed maximum",
        "string_pattern_mismatch": "String does not match the required format",
        "enum": "Input is not an allowed value",
    }
    return messages.get(error_type, "Invalid value")
