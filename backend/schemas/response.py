"""VisionOps AI — Generic API Response Schemas.

This module defines the standard response envelope schemas used to wrap
API payloads consistently across the entire backend.

Contents:
    - :class:`SuccessResponse` — generic success envelope with optional
      message and typed payload.
    - :class:`ErrorResponse` — structured error envelope carrying an
      error code, human-readable message, optional details, and a
      request correlation id.
    - :class:`PaginatedResponse` — generic pagination envelope that
      wraps a list of items with pagination metadata.

These schemas are intended to be used as FastAPI ``response_model``
definitions so OpenAPI documentation reflects a predictable envelope.

Usage:
    from backend.schemas.response import (
        SuccessResponse,
        ErrorResponse,
        PaginatedResponse,
    )

The ``Generic`` type parameter allows type-safe payloads while keeping a
single, DRY envelope implementation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Generic, Sequence, TypeVar

from pydantic import Field, field_validator

from backend.schemas.common import BaseSchema

# ---------------------------------------------------------------------------
# Type Variables
# ---------------------------------------------------------------------------

DataT = TypeVar("DataT")


# ---------------------------------------------------------------------------
# Success Response
# ---------------------------------------------------------------------------


class SuccessResponse(BaseSchema, Generic[DataT]):
    """Standard success envelope for API responses.

    Attributes:
        success: Always ``True`` for success responses.
        message: Optional human-readable success message.
        data: The typed payload being returned.
        timestamp: ISO-8601 UTC timestamp of the response.
    """

    success: Annotated[
        bool,
        Field(
            default=True,
            description="Indicates the request succeeded.",
            examples=[True],
        ),
    ]
    message: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional human-readable success message.",
            examples=["Operation completed successfully."],
        ),
    ] = None
    data: Annotated[
        DataT | None,
        Field(description="The response payload."),
    ] = None
    timestamp: Annotated[
        datetime,
        Field(
            default_factory=lambda: datetime.now(timezone.utc),
            description="ISO-8601 UTC timestamp of the response.",
        ),
    ]

    @field_validator("timestamp", mode="before")
    @classmethod
    def _normalize_timestamp(cls, value: datetime | str) -> datetime:
        """Normalize a naive timestamp to timezone-aware UTC.

        Args:
            value: Raw timestamp (``datetime`` or ISO-8601 string).

        Returns:
            A timezone-aware UTC datetime.
        """
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            parsed = value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @field_validator("success")
    @classmethod
    def _success_must_be_true(cls, value: bool) -> bool:
        """Guard against constructing a success envelope with ``False``.

        Args:
            value: The success flag.

        Returns:
            The validated value.

        Raises:
            ValueError: If *value* is not ``True``.
        """
        if value is not True:
            raise ValueError("SuccessResponse.success must always be True.")
        return value


# ---------------------------------------------------------------------------
# Error Response
# ---------------------------------------------------------------------------


class ErrorResponse(BaseSchema):
    """Structured error envelope returned on API failures.

    Attributes:
        success: Always ``False`` for error responses.
        error_code: Machine-readable error code (e.g. ``NOT_FOUND``).
        message: Human-readable error message.
        details: Optional structured error details (e.g. field errors).
        request_id: Optional correlation id for tracing.
        timestamp: ISO-8601 UTC timestamp of the error.
    """

    success: Annotated[
        bool,
        Field(
            default=False,
            description="Always ``False`` for error responses.",
            examples=[False],
        ),
    ]
    error_code: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description=(
                "Machine-readable error code, e.g. ``VALIDATION_ERROR``."
            ),
            examples=["VALIDATION_ERROR"],
        ),
    ]
    message: Annotated[
        str,
        Field(
            min_length=1,
            max_length=1000,
            description="Human-readable error message.",
            examples=["A validation error occurred."],
        ),
    ]
    details: Annotated[
        dict[str, object] | list[dict[str, object]] | None,
        Field(
            default=None,
            description=(
                "Optional structured error details (e.g. per-field "
                "validation errors)."
            ),
        ),
    ] = None
    request_id: Annotated[
        str | None,
        Field(
            default=None,
            max_length=128,
            description="Optional correlation id for request tracing.",
            examples=["req_01HXZ..."],
        ),
    ] = None
    timestamp: Annotated[
        datetime,
        Field(
            default_factory=lambda: datetime.now(timezone.utc),
            description="ISO-8601 UTC timestamp of the error.",
        ),
    ]

    @field_validator("error_code", "message")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        """Reject empty/whitespace-only error codes and messages.

        Args:
            value: The error code or message.

        Returns:
            The stripped, non-empty value.

        Raises:
            ValueError: If the value is empty or whitespace-only.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("Error code and message must not be empty.")
        return stripped

    @field_validator("success")
    @classmethod
    def _success_must_be_false(cls, value: bool) -> bool:
        """Guard against constructing an error envelope with ``True``.

        Args:
            value: The success flag.

        Returns:
            The validated value.

        Raises:
            ValueError: If *value* is not ``False``.
        """
        if value is not False:
            raise ValueError("ErrorResponse.success must always be False.")
        return value


# ---------------------------------------------------------------------------
# Paginated Response
# ---------------------------------------------------------------------------


class PaginatedResponse(BaseSchema, Generic[DataT]):
    """Generic paginated list envelope.

    Attributes:
        items: The page of typed items.
        total: Total number of matching items across all pages.
        limit: Maximum items per page (1–1000).
        offset: Number of items skipped.
        page: 1-based current page number (derived).
        has_more: Whether additional pages exist (derived).
    """

    items: Annotated[
        Sequence[DataT],
        Field(description="The page of items."),
    ]
    total: Annotated[
        int,
        Field(ge=0, description="Total matching items across all pages."),
    ]
    limit: Annotated[
        int,
        Field(default=100, ge=1, le=1000, description="Max items per page."),
    ] = 100
    offset: Annotated[
        int,
        Field(default=0, ge=0, description="Number of items skipped."),
    ] = 0

    @field_validator("total")
    @classmethod
    def _total_non_negative(cls, value: int) -> int:
        """Ensure the total count is non-negative.

        Args:
            value: Total item count.

        Returns:
            The validated count.

        Raises:
            ValueError: If the count is negative.
        """
        if value < 0:
            raise ValueError(f"total must be >= 0, got {value}.")
        return value

    @property
    def page(self) -> int:
        """Return the 1-based current page number.

        Returns:
            ``offset // limit + 1`` when *limit* > 0, otherwise ``1``.
        """
        if self.limit <= 0:
            return 1
        return (self.offset // self.limit) + 1

    @property
    def has_more(self) -> bool:
        """Return whether additional pages exist.

        Returns:
            ``True`` if ``offset + len(items) < total``.
        """
        return (self.offset + len(self.items)) < self.total


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "SuccessResponse",
    "ErrorResponse",
    "PaginatedResponse",
]

