"""Standard error envelope and exception handlers.

Every error the API produces uses one response shape:

``{"error": {"code": ..., "message": ..., "details": {...}}}``

Clients therefore parse errors with a single code path: map ``code`` to
behavior (retry, show a message, log), display ``message`` to a person, and
inspect ``details`` when a code needs specifics. Without an envelope, each
endpoint would invent its own shape and every client would need per-endpoint
error handling.

The unhandled-exception handler never puts a stack trace in the response body:
trace details leak internals (file paths, library versions) to whoever can
reach the API. The traceback goes to the logs, where operators can see it.
"""

from typing import Any

import structlog
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.middleware import get_request_id


class AppException(Exception):
    """Base class for expected, application-raised errors.

    Attributes:
        status_code: HTTP status code carried by the subclass.
        code: Stable machine-readable error code carried by the subclass.
        message: Human-readable default message carried by the subclass.
        details: Optional structured context (field names, limits, ids).
    """

    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    message: str = "Internal server error."
    details: dict[str, Any]

    def __init__(self, details: dict[str, Any] | None = None) -> None:
        """Create the exception with optional structured details.

        Args:
            details: Structured context; defaults to an empty dict.
        """
        self.details = details or {}
        super().__init__(self.message)


class UnauthorizedException(AppException):
    """The request lacks valid authentication credentials."""

    status_code = 401
    code = "UNAUTHORIZED"
    message = "Authentication is required."


class ForbiddenException(AppException):
    """The authenticated caller lacks the required role."""

    status_code = 403
    code = "FORBIDDEN"
    message = "You do not have permission to perform this action."


class NotFoundException(AppException):
    """The requested resource does not exist."""

    status_code = 404
    code = "NOT_FOUND"
    message = "Resource not found."


class ValidationException(AppException):
    """The request data failed validation."""

    status_code = 400
    code = "VALIDATION_ERROR"
    message = "The submitted data is invalid."


class RateLimitException(AppException):
    """The caller exceeded the allowed request rate."""

    status_code = 429
    code = "RATE_LIMITED"
    message = "Too many requests."


class InternalErrorException(AppException):
    """An unexpected error occurred inside the application."""

    status_code = 500
    code = "INTERNAL_ERROR"
    message = "Internal server error."


class ErrorBody(BaseModel):
    """The ``error`` object inside every error response.

    ``details`` is a dict for application errors and a list for request
    validation errors, where FastAPI's ``exc.errors()`` is a list of
    per-field error objects.
    """

    code: str
    message: str
    details: dict[str, Any] | list[Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """Envelope wrapping :class:`ErrorBody` under a single ``error`` key."""

    error: ErrorBody


def _envelope_response(
    status_code: int, code: str, message: str, details: dict[str, Any] | list[Any]
) -> JSONResponse:
    """Render the standard error envelope as a JSONResponse."""
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Render an application-raised AppException in the standard envelope."""
    return _envelope_response(exc.status_code, exc.code, exc.message, exc.details)


def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Render request validation failures (HTTP 422) in the standard envelope.

    ``exc.errors()`` is placed in ``details`` so clients can see exactly which
    fields failed and why, in FastAPI/Pydantic's native error structure.
    """
    return _envelope_response(
        422, "VALIDATION_ERROR", "Request validation failed.", list(exc.errors())
    )


def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Render Starlette/FastAPI HTTPException in the standard envelope.

    A string ``detail`` is normalized to an UPPER_SNAKE ``code`` (Starlette's
    default 404 detail "Not Found" becomes "NOT_FOUND") and kept verbatim as
    the human-readable ``message``.
    """
    if isinstance(exc.detail, str):
        return _envelope_response(
            exc.status_code, exc.detail.upper().replace(" ", "_"), exc.detail, {}
        )
    return _envelope_response(exc.status_code, "HTTP_ERROR", "HTTP error.", {})


def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render any unhandled exception as a generic 500 in the standard envelope.

    The exception is logged with the request id for correlation; the response
    body never contains a stack trace or internal details.
    """
    logger = structlog.get_logger(__name__)
    logger.error(
        "unhandled_exception",
        request_id=get_request_id(),
        path=request.url.path,
        error=repr(exc),
        exc_info=True,
    )
    return _envelope_response(500, "INTERNAL_ERROR", "Unexpected server error.", {})
