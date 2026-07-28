"""
AI-specific exception hierarchy for the H.I.R.E. AI subsystem.

Every exception in this module derives from `AIException`, which itself
inherits from `app.core.exceptions.HireException`. This means AI errors
are automatically caught and formatted by the global exception handler
registered in HIRE-BE-004 — no separate error-handling path is needed
for the AI subsystem.

This module contains only the base framework's exception hierarchy.
Business-specific exceptions (e.g. resume-parsing errors) belong to
whichever future ticket introduces that Intelligence System.
"""

from fastapi import status

from app.core.exceptions import HireException


class AIException(HireException):
    """
    Base exception for all errors raised within the AI subsystem.

    Future Intelligence Systems that need their own AI-related
    exceptions should inherit from this class (or one of its
    subclasses below) rather than from HireException directly, so
    that AI errors remain identifiable as a distinct category while
    still being handled by the existing global exception framework.
    """

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_type: str = "AIException",
    ) -> None:
        super().__init__(message=message, status_code=status_code, error_type=error_type)


class ContextValidationException(AIException):
    """
    Raised when an AIContext does not satisfy what an engine requires.

    Typically raised from an engine's `validate_context` override when
    expected fields are missing or malformed in `context.data`.
    """

    def __init__(self, message: str = "The provided AI context is invalid.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_type="ContextValidationError",
        )


class EngineRegistrationException(AIException):
    """
    Raised for any EngineRegistry error, including duplicate
    registration and lookup of a name with no registered engine.
    """

    def __init__(self, message: str = "Engine registration or lookup failed.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_type="EngineRegistrationError",
        )


class EngineExecutionException(AIException):
    """
    Raised when an engine fails during its own execution lifecycle
    (e.g. it returns a result that fails validation).
    """

    def __init__(self, message: str = "Engine execution failed.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="EngineExecutionError",
        )


class OrchestrationException(AIException):
    """
    Raised when the AIOrchestrator cannot complete a workflow, including
    when a registered engine raises an unexpected (non-AI) exception
    during orchestration.
    """

    def __init__(self, message: str = "AI workflow orchestration failed.") -> None:
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_type="OrchestrationError",
        )