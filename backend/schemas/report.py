"""VisionOps AI — Report Domain Schemas.

Pydantic v2 schemas for report generation, export requests, and report
metadata. These map directly to the interfaces exposed by
:mod:`backend.services.report_service` and the reports API.

Contents:
    - :class:`ReportRequest` — request body for generating a report.
    - :class:`ReportResponse` — response payload for a generated report.
    - :class:`ReportMetadata` — metadata describing a report record.
    - :class:`ExportRequest` — request body for exporting data.

Validation covers required fields, report format enumeration, file
extensions, date ranges, and metric names.

Usage:
    from backend.schemas.report import (
        ReportRequest, ReportResponse, ReportMetadata, ExportRequest,
    )
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import Field, field_validator

from backend.schemas.common import BaseSchema, ReportFormat

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPORT_ID_PREFIX: str = "rpt_"


# ---------------------------------------------------------------------------
# Report Request
# ---------------------------------------------------------------------------


class ReportRequest(BaseSchema):
    """Request body for generating a report.

    Attributes:
        format: Report export format.
        video_id: Optional video identifier to scope the report.
        date_from: Optional start date for report data (YYYY-MM-DD).
        date_to: Optional end date for report data (YYYY-MM-DD).
        include_detections: Whether to include detection data.
        include_alerts: Whether to include alert data.
        include_kpis: Whether to include KPI data.
        include_events: Whether to include event data.
        title: Optional custom report title.

    Example:
        .. code-block:: json

            {
                "format": "pdf",
                "video_id": "vid_001",
                "date_from": "2025-01-01",
                "date_to": "2025-01-31",
                "include_detections": true,
                "include_alerts": true,
                "include_kpis": true,
                "title": "Warehouse Report - January 2025"
            }
    """

    format: Annotated[
        ReportFormat,
        Field(description="Report export format.", examples=["pdf"]),
    ]
    video_id: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description="Optional video identifier to scope the report.",
        ),
    ] = None
    date_from: Annotated[
        str | None,
        Field(
            default=None,
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            description="Optional start date (YYYY-MM-DD).",
            examples=["2025-01-01"],
        ),
    ] = None
    date_to: Annotated[
        str | None,
        Field(
            default=None,
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            description="Optional end date (YYYY-MM-DD).",
            examples=["2025-01-31"],
        ),
    ] = None
    include_detections: Annotated[
        bool,
        Field(
            default=True,
            description="Include detection data in the report.",
        ),
    ] = True
    include_alerts: Annotated[
        bool,
        Field(
            default=True,
            description="Include alert data in the report.",
        ),
    ] = True
    include_kpis: Annotated[
        bool,
        Field(
            default=True,
            description="Include KPI data in the report.",
        ),
    ] = True
    include_events: Annotated[
        bool,
        Field(
            default=False,
            description="Include event data in the report.",
        ),
    ] = False
    title: Annotated[
        str | None,
        Field(
            default=None,
            max_length=200,
            description="Optional custom report title.",
            examples=["Warehouse Report - January 2025"],
        ),
    ] = None

    @field_validator("format", mode="before")
    @classmethod
    def _coerce_format(cls, value: str | ReportFormat) -> ReportFormat:
        """Coerce raw format strings into the :class:`ReportFormat` enum."""
        if isinstance(value, ReportFormat):
            return value
        try:
            return ReportFormat(value.strip().lower())
        except ValueError:
            valid = ", ".join(sorted(f.value for f in ReportFormat))
            raise ValueError(
                f"Invalid format '{value}'. Valid formats: {valid}."
            ) from None

    @field_validator("date_from", "date_to")
    @classmethod
    def _validate_date_format(cls, value: str | None) -> str | None:
        """Ensure dates match YYYY-MM-DD if provided."""
        if value is None:
            return None
        from re import match as re_match
        if not re_match(r"^\d{4}-\d{2}-\d{2}$", value):
            raise ValueError(
                f"Invalid date '{value}'. Expected format: YYYY-MM-DD."
            )
        return value


# ---------------------------------------------------------------------------
# Report Response
# ---------------------------------------------------------------------------


class ReportResponse(BaseSchema):
    """Response payload for a generated report.

    Mirrors the shape returned by
    :meth:`ReportService.generate_report
    <backend.services.report_service.ReportService.generate_report>`.

    Attributes:
        report_id: Unique report identifier (``rpt_...``).
        format: Report format.
        status: Generation status (``"generated"``, ``"failed"``).
        file_path: Path to the generated report file.
        file_size: Optional file size in bytes.
        title: Optional report title.
        message: Optional status message.
        generated_at: ISO-8601 generation timestamp.
    """

    report_id: Annotated[
        str,
        Field(
            min_length=1,
            description="Unique report identifier (prefix 'rpt_').",
            examples=["rpt_001"],
        ),
    ]
    format: Annotated[
        str,
        Field(description="Report format.", examples=["pdf"]),
    ]
    status: Annotated[
        str,
        Field(
            pattern=r"^(generated|failed|pending)$",
            description="Generation status.",
            examples=["generated"],
        ),
    ]
    file_path: Annotated[
        str,
        Field(
            min_length=1,
            description="Path to the generated report file.",
        ),
    ]
    file_size: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Optional file size in bytes.",
        ),
    ] = None
    title: Annotated[
        str | None,
        Field(
            default=None,
            max_length=200,
            description="Optional report title.",
        ),
    ] = None
    message: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional status message.",
        ),
    ] = None
    generated_at: Annotated[
        datetime,
        Field(description="ISO-8601 generation timestamp."),
    ]

    @field_validator("report_id")
    @classmethod
    def _validate_report_id(cls, value: str) -> str:
        """Validate the report identifier prefix and non-emptiness."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("report_id must not be empty.")
        if not stripped.startswith(_REPORT_ID_PREFIX):
            raise ValueError(
                f"report_id must start with '{_REPORT_ID_PREFIX}'."
            )
        return stripped

    @field_validator("format")
    @classmethod
    def _validate_format(cls, value: str) -> str:
        """Normalize format to lowercase."""
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("format must not be empty.")
        return normalized

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        """Normalize status to lowercase."""
        normalized = value.strip().lower()
        if normalized not in ("generated", "failed", "pending"):
            raise ValueError(
                f"Invalid status '{value}'. Must be one of: "
                f"generated, failed, pending."
            )
        return normalized

    @field_validator("file_path")
    @classmethod
    def _file_path_not_empty(cls, value: str) -> str:
        """Reject empty file paths."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("file_path must not be empty.")
        return stripped

    @field_validator("generated_at", mode="before")
    @classmethod
    def _normalize_timestamp(cls, value: datetime | str) -> datetime:
        """Normalize naive timestamps to timezone-aware UTC."""
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            parsed = value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Report Metadata
# ---------------------------------------------------------------------------


class ReportMetadata(BaseSchema):
    """Metadata describing a stored report record.

    Attributes:
        report_id: Unique report identifier.
        format: Report format.
        title: Optional report title.
        file_path: File path to the report.
        file_size: File size in bytes.
        video_id: Optional associated video identifier.
        date_from: Optional start date of report scope.
        date_to: Optional end date of report scope.
        created_at: ISO-8601 creation timestamp.
        status: Generation status.
    """

    report_id: Annotated[
        str,
        Field(min_length=1, description="Unique report identifier."),
    ]
    format: Annotated[
        ReportFormat,
        Field(description="Report format."),
    ]
    title: Annotated[
        str | None,
        Field(
            default=None,
            max_length=200,
            description="Optional report title.",
        ),
    ] = None
    file_path: Annotated[
        str,
        Field(min_length=1, description="File path to the report."),
    ]
    file_size: Annotated[
        int,
        Field(ge=0, default=0, description="File size in bytes."),
    ] = 0
    video_id: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description="Optional associated video identifier.",
        ),
    ] = None
    date_from: Annotated[
        str | None,
        Field(
            default=None,
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            description="Optional start date of scope.",
        ),
    ] = None
    date_to: Annotated[
        str | None,
        Field(
            default=None,
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            description="Optional end date of scope.",
        ),
    ] = None
    created_at: Annotated[
        datetime,
        Field(description="ISO-8601 creation timestamp."),
    ]
    status: Annotated[
        str,
        Field(
            pattern=r"^(generated|failed|pending)$",
            description="Generation status.",
        ),
    ]

    @field_validator("report_id", "file_path")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        """Reject empty string fields."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field must not be empty.")
        return stripped

    @field_validator("format", mode="before")
    @classmethod
    def _coerce_format(cls, value: str | ReportFormat) -> ReportFormat:
        """Coerce raw format strings into the :class:`ReportFormat` enum."""
        if isinstance(value, ReportFormat):
            return value
        try:
            return ReportFormat(value.strip().lower())
        except ValueError:
            valid = ", ".join(sorted(f.value for f in ReportFormat))
            raise ValueError(
                f"Invalid format '{value}'. Valid formats: {valid}."
            ) from None

    @field_validator("created_at", mode="before")
    @classmethod
    def _normalize_timestamp(cls, value: datetime | str) -> datetime:
        """Normalize naive timestamps to timezone-aware UTC."""
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            parsed = value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Export Request
# ---------------------------------------------------------------------------


class ExportRequest(BaseSchema):
    """Request body for exporting raw data.

    Attributes:
        data_type: The type of data to export (e.g. ``"detections"``,
            ``"alerts"``, ``"kpis"``, ``"events"``).
        format: Export format (``"csv"``, ``"json"``, ``"excel"``).
        video_id: Optional video identifier to scope the export.
        date_from: Optional start date (YYYY-MM-DD).
        date_to: Optional end date (YYYY-MM-DD).
        limit: Maximum number of records to export.
    """

    data_type: Annotated[
        str,
        Field(
            min_length=1,
            description="Type of data to export.",
            examples=["detections"],
        ),
    ]
    format: Annotated[
        str,
        Field(
            default="csv",
            pattern=r"^(csv|json|excel)$",
            description="Export format.",
            examples=["csv"],
        ),
    ] = "csv"
    video_id: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description="Optional scoped video identifier.",
        ),
    ] = None
    date_from: Annotated[
        str | None,
        Field(
            default=None,
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            description="Optional start date (YYYY-MM-DD).",
        ),
    ] = None
    date_to: Annotated[
        str | None,
        Field(
            default=None,
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            description="Optional end date (YYYY-MM-DD).",
        ),
    ] = None
    limit: Annotated[
        int,
        Field(
            default=1000,
            ge=1,
            le=100000,
            description="Maximum records to export.",
        ),
    ] = 1000

    @field_validator("data_type")
    @classmethod
    def _validate_data_type(cls, value: str) -> str:
        """Validate and normalize the data type."""
        normalized = value.strip().lower()
        valid_types = {"detections", "alerts", "kpis", "events", "videos"}
        if normalized not in valid_types:
            raise ValueError(
                f"Invalid data_type '{value}'. "
                f"Valid: {', '.join(sorted(valid_types))}."
            )
        return normalized

    @field_validator("format")
    @classmethod
    def _validate_export_format(cls, value: str) -> str:
        """Normalize export format."""
        normalized = value.strip().lower()
        if normalized not in ("csv", "json", "excel"):
            raise ValueError(
                f"Invalid format '{value}'. Valid: csv, json, excel."
            )
        return normalized


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "ReportRequest",
    "ReportResponse",
    "ReportMetadata",
    "ExportRequest",
]

