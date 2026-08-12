"""
Standardized API response models for H.I.R.E.

This module is the single source of success-response shapes for the
entire backend. Every endpoint that returns a successful result should
return a `SuccessResponse`, so that clients can rely on one consistent
envelope across the whole API.

This complements HIRE-BE-004's exception framework, which already
standardizes error responses. Together they form the complete API
response contract:

    Success -> SuccessResponse  (this module)
    Failure -> app.core.exceptions handlers

Usage:
    from app.schemas.responses import SuccessResponse

    # Untyped / mixed payloads
    return SuccessResponse(message="Login successful.", data={"token": "..."})

    # No payload
    return SuccessResponse(message="Resume deleted successfully.")

    # Typed payload, for accurate OpenAPI docs on a specific endpoint
    @router.get("/employees", response_model=SuccessResponse[list[EmployeeOut]])
    def list_employees() -> SuccessResponse[list[EmployeeOut]]:
        return SuccessResponse(message="Employees retrieved successfully.", data=employees)
"""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """
    Generic success response envelope.

    Every successful API response follows the same shape:

        {
            "success": true,
            "message": "Operation completed successfully.",
            "data": {}
        }

    `data` accepts any payload type — an object, a list, a dictionary,
    a primitive value, or null — so this single model covers every
    success case without needing a separate response class per
    endpoint.

    Endpoints that want the payload type reflected in their OpenAPI
    schema can subscript this model, e.g. `SuccessResponse[UserOut]`
    or `SuccessResponse[list[UserOut]]`. Endpoints that don't need
    that level of documentation can construct it directly without
    subscripting, as shown in the module docstring.
    """

    success: Literal[True] = Field(
        default=True,
        description="Always true for a SuccessResponse; failures are handled separately.",
    )
    message: str = Field(
        default="Operation completed successfully.",
        description="Human-readable summary of the result.",
    )
    data: T | None = Field(
        default=None,
        description=(
            "Response payload. May be an object, list, dictionary, "
            "primitive value, or null for endpoints with no payload."
        ),
    )