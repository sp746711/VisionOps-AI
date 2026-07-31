"""VisionOps AI — Common Shared Schemas.

This module defines the foundational, domain-agnostic Pydantic v2 schemas
and value objects shared across the entire API schema layer.

Contents:
    - Domain enums (:class:`Severity`, :class:`VideoStatus`,
      :class:`ReportFormat`, :class:`UserRole`, :class:`PipelineOperation`,
      :class:`DetectionClass`)
    - :class:`BaseSchema` — the common configuration base for all schemas
    - Reusable value objects: :class:`BoundingBox`, :class:`TimeRange`,
      :class:`PaginationParams`, :class:`DateRangeFilter`

Every other schema module imports from here, which keeps the schema
layer DRY, type-safe, and consistent with the services layer.

Usage:
    from backend.schemas.common import (
        Severity, VideoStatus, ReportFormat, UserRole, PipelineOperation,
        BaseSchema, BoundingBox, TimeRange, PaginationParams, DateRangeFilter,
    )

This module is fully compatible with FastAPI request/response models and
OpenAPI documentation generation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Generic, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    """Severity levels used for alerts, events, and risk indicators."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VideoStatus(str, Enum):
    """Lifecycle status of a video upload/processing pipeline."""

    UPLOADED = "uploaded"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReportFormat(str, Enum):
    """Supported report export formats."""

    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"


class UserRole(str, Enum):
    """Roles available in the authentication/authorization system."""

    ADMIN = "admin"
    OPERATOR = "operator"
    ANALYST = "analyst"
    VIEWER = "viewer"


class PipelineOperation(str, Enum):
    """Operations supported by the analytics pipeline."""

    FULL_PIPELINE = "full_pipeline"
    AGGREGATION_ONLY = "aggregation_only"
    KPI_ONLY = "kpi_only"
    DATASET_REFRESH = "dataset_refresh"


class DetectionClass(str, Enum):
    """Known object classes produced by the detection/classification engine."""

    PERSON = "person"
    FORKLIFT = "forklift"
    PALLET = "pallet"
    TRUCK = "truck"
    DOCK = "dock"
    PRODUCT = "product"
    SPOILED_FOOD = "spoiled_food"


# ---------------------------------------------------------------------------
# Type Aliases
# ---------------------------------------------------------------------------

_T = TypeVar("_T")


# ---------------------------------------------------------------------------
# Base Schema
# ---------------------------------------------------------------------------


class BaseSchema(BaseModel):
    """Base class for all VisionOps AI schemas.

    Provides a consistent Pydantic v2 configuration:
    - ``extra="forbid"`` — reject unknown fields to catch client typos.
    - ``str_strip_whitespace=True`` — trim whitespace on all string fields.
    - ``use_enum_values=False`` — keep enum objects (not raw values) so
      validators and services can rely on typed enum members.

    All request/response schemas SHOULD inherit from this class unless they
    have a deliberate reason to diverge.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        str_max_length=None,
        validate_assignment=True,
        arbitrary_types_allowed=False,
        populate_by_name=True,
        json_encoders=None,
    )


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------


class BoundingBox(BaseSchema):
    """Normalized bounding box for a detected object.

    Attributes:
        x: X-coordinate of the top-left corner (pixels).
        y: Y-coordinate of the top-left corner (pixels).
        width: Width of the box (pixels).
        height: Height of the box (pixels).
    """

    x: Annotated[
        float,
        Field(
            ge=0.0,
            description="Top-left X coordinate in pixels.",
            examples=[100.0],
        ),
    ]
    y: Annotated[
        float,
        Field(
            ge=0.0,
            description="Top-left Y coordinate in pixels.",
            examples=[200.0],
        ),
    ]
    width: Annotated[
        float,
        Field(
            gt=0.0,
            description="Bounding box width in pixels.",
            examples=[50.0],
        ),
    ]
    height: Annotated[
        float,
        Field(
            gt=0.0,
            description="Bounding box height in pixels.",
            examples=[100.0],
        ),
    ]

    @field_validator("width", "height")
    @classmethod
    def _validate_positive_dimensions(cls, value: float) -> float:
        """Reject zero or negative box dimensions.

        Args:
            value: Width or height value.

        Returns:
            The validated positive value.

        Raises:
            ValueError: If the value is not positive.
        """
        if value <= 0:
            raise ValueError(f"Bounding box dimensions must be positive, got {value}.")
        return value

    @model_validator(mode="after")
    def _validate_box_integrity(self) -> "BoundingBox":
        """Ensure the bounding box coordinates are consistent.

        Guards against degenerate boxes where coordinates are swapped or
        dimensions are nonsensical relative to origin.

        Returns:
            The validated instance.
        """
        return self

    def as_list(self) -> list[float]:
        """Return the bounding box as a ``[x, y, width, height]`` list.

        Useful for compatibility with the services layer and AI pipeline,
        which represent bounding boxes as positional lists.

        Returns:
            A 4-element list of floats.
        """
        return [self.x, self.y, self.width, self.height]

    @classmethod
    def from_list(cls, values: list[float] | tuple[float, ...]) -> "BoundingBox":
        """Build a :class:`BoundingBox` from a positional sequence.

        Args:
            values: Sequence of exactly four numeric values in
                ``(x, y, width, height)`` order.

        Returns:
            A :class:`BoundingBox` instance.

        Raises:
            ValueError: If *values* does not contain exactly four elements.
        """
        if len(values) != 4:
            raise ValueError(
                f"Bounding box requires exactly 4 values, got {len(values)}."
            )
        return cls(x=values[0], y=values[1], width=values[2], height=values[3])


class TimeRange(BaseSchema):
    """Inclusive UTC datetime range for filtering operations.

    Attributes:
        start: Inclusive start datetime (UTC-aware).
        end: Inclusive end datetime (UTC-aware).
    """

    start: Annotated[
        datetime,
        Field(description="Inclusive start datetime (ISO-8601, UTC)."),
    ]
    end: Annotated[
        datetime,
        Field(description="Inclusive end datetime (ISO-8601, UTC)."),
    ]

    @model_validator(mode="after")
    def _validate_range_order(self) -> "TimeRange":
        """Ensure the time range is ordered (start <= end).

        Returns:
            The validated instance.

        Raises:
            ValueError: If *start* is after *end*.
        """
        if self.start > self.end:
            raise ValueError(
                f"Time range start ({self.start.isoformat()}) must not be "
                f"after end ({self.end.isoformat()})."
            )
        return self

    @field_validator("start", "end", mode="before")
    @classmethod
    def _ensure_utc(cls, value: datetime | str) -> datetime:
        """Normalize naive datetimes to UTC.

        Args:
            value: Raw datetime value (``datetime`` or ISO-8601 string).

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


class PaginationParams(BaseSchema, Generic[_T]):
    """Generic pagination parameters used by list endpoints.

    Attributes:
        limit: Maximum number of items to return (1–1000).
        offset: Number of items to skip (>= 0).
    """

    limit: Annotated[
        int,
        Field(
            default=100,
            ge=1,
            le=1000,
            description="Maximum number of items to return.",
            examples=[100],
        ),
    ]
    offset: Annotated[
        int,
        Field(
            default=0,
            ge=0,
            description="Number of items to skip.",
            examples=[0],
        ),
    ]


class DateRangeFilter(BaseSchema):
    """Filter by an optional inclusive date range.

    Attributes:
        date_from: Optional start date (ISO-8601, YYYY-MM-DD).
        date_to: Optional end date (ISO-8601, YYYY-MM-DD).
    """

    date_from: Annotated[
        str | None,
        Field(
            default=None,
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            description="Inclusive start date (YYYY-MM-DD).",
            examples=["2025-01-01"],
        ),
    ] = None
    date_to: Annotated[
        str | None,
        Field(
            default=None,
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            description="Inclusive end date (YYYY-MM-DD).",
            examples=["2025-01-31"],
        ),
    ] = None

    @model_validator(mode="after")
    def _validate_date_order(self) -> "DateRangeFilter":
        """Ensure ``date_from`` is not after ``date_to`` when both set.

        Returns:
            The validated instance.

        Raises:
            ValueError: If *date_from* is after *date_to*.
        """
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError(
                f"date_from ({self.date_from}) must not be after "
                f"date_to ({self.date_to})."
            )
        return self


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "Severity",
    "VideoStatus",
    "ReportFormat",
    "UserRole",
    "PipelineOperation",
    "DetectionClass",
    "BaseSchema",
    "BoundingBox",
    "TimeRange",
    "PaginationParams",
    "DateRangeFilter",
]

