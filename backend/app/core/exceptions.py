"""
Centralized exception handling framework for H.I.R.E.

This module is the single error-handling layer for the entire backend.
It provides:

- `HireException`, a base exception that all future custom application
  exceptions should inherit from.
- A small set of reusable, generic exception subclasses covering common
  API error categories (not found, validation, auth, conflict).
- Global FastAPI exception handlers for HireException, HTTPException,
  request validation errors, and any unhandled exception.
- `register_exception_handlers(app)`, called once from main.py, which
  wires all of the above into the FastAPI application.

No endpoint should need its own try/except block for these common
error categories; raising the appropriate exception is sufficient.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Base exception and reusable, generic subclasses
# ---------------------------------------------------------------------------


class HireException(Exception):
    """
    Base exception for all H.I.R.E.-specific application errors.

    Future custom exceptions (e.g. resume-specific or interview-specific
    errors introduced by later tickets) should inherit from this class.
    Doing so is sufficient for them to be caught and formatted correctly
    by `hire_exception_handler` below, with no changes required to the
    handler or to `register_exception_handlers`.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_type: str = "HireException",
    ) -> None:
        """
        Args:
            message: Human-readable, client-safe description of the error.
            status_code: HTTP status code to return for this error.
            error_type: Short machine-readable label included in the
                standardized error response.
        """
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(message)


class ResourceNotFoundException(HireException):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str = "The requested resource was not found.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_type="ResourceNotFound",
        )


class ValidationException(HireException):
    """Raised when request data fails application-level validation."""

    def __init__(self, message: str = "Invalid request data.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_type="ValidationError",
        )


class AuthenticationException(HireException):
    """Raised when a request cannot be authenticated."""

    def __init__(self, message: str = "Authentication failed.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_type="AuthenticationError",
        )


class AuthorizationException(HireException):
    """Raised when an authenticated caller lacks permission for an action."""

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_type="AuthorizationError",
        )


class ConflictException(HireException):
    """Raised when a request conflicts with the current state of a resource."""

    def __init__(
        self,
        message: str = "The request conflicts with the current state of the resource.",
    ) -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_type="ConflictError",
        )


# ---------------------------------------------------------------------------
# Standard error response envelope
# ---------------------------------------------------------------------------


def _build_error_response(status_code: int, error_type: str, message: str) -> JSONResponse:
    """
    Build the standardized H.I.R.E. error response body.

    Every handled error, regardless of its source, is returned in this
    same lightweight shape:

        {
            "success": false,
            "error": {
                "type": "...",
                "message": "..."
            }
        }
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "type": error_type,
                "message": message,
            },
        },
    )


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def hire_exception_handler(request: Request, exc: HireException) -> JSONResponse:
    """Handle HireException and any exception derived from it."""
    logger.warning("%s: %s", exc.error_type, exc.message)
    return _build_error_response(exc.status_code, exc.error_type, exc.message)


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle FastAPI/Starlette HTTPException, standardizing the response shape."""
    logger.warning("HTTPException %s on %s: %s", exc.status_code, request.url.path, exc.detail)
    return _build_error_response(exc.status_code, "HTTPException", str(exc.detail))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Handle FastAPI request validation errors.

    Replaces FastAPI's default validation error body with the
    standardized H.I.R.E. response format. The detailed field-level
    errors are logged for debugging but not returned to the client,
    keeping the response lightweight per the ticket's requirements.
    """
    logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
    return _build_error_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "ValidationError",
        "Invalid request data.",
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for any exception not otherwise handled.

    Full exception details, including the traceback, are written to the
    centralized log via logger.exception(). The client only ever
    receives a generic, safe message with no traceback, file paths, or
    other internal details.
    """
    logger.exception("Unhandled exception on %s", request.url.path)
    return _build_error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "InternalServerError",
        "An unexpected error occurred. Please try again later.",
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all global exception handlers on the given FastAPI app.

    Called once from main.py during application setup. No individual
    route or router needs to register its own handlers.
    """
    app.add_exception_handler(HireException, hire_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)