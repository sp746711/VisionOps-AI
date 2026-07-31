"""VisionOps AI — Analytics Domain Schemas.

Pydantic v2 schemas for the analytics pipeline, KPI calculations,
spoilage metrics, freshness metrics, and trend analysis. These map
directly to the interfaces exposed by
:mod:`backend.services.analytics_service` and the analytics API.

Contents:
    - :class:`AnalyticsRequest` — request body for running analytics.
    - :class:`AnalyticsResponse` — response payload for an analytics run.
    - :class:`KPIResponse` — a single KPI record.
    - :class:`DashboardMetrics` — top-level dashboard metrics.
    - :class:`TrendResponse` — time-series trend data.
    - :class:`SpoilageMetrics` — spoilage risk assessment.
    - :class:`FreshnessMetrics` — freshness and turnover analysis.

Validation covers required fields, confidence values, operation
enumeration, metric names, date formatting, and numeric ranges.

Usage:
    from backend.schemas.analytics import (
        AnalyticsRequest, AnalyticsResponse, KPIResponse,
        DashboardMetrics, TrendResponse, SpoilageMetrics, FreshnessMetrics,
    )
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import Field, field_validator

from backend.schemas.common import BaseSchema, PipelineOperation

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_METRICS: frozenset[str] = frozenset({
    "total_detections",
    "unique_classes",
    "average_confidence",
    "spoilage_risk_index",
    "freshness_score",
    "videos_processed",
    "alerts_generated",
    "events_detected",
})


# ---------------------------------------------------------------------------
# Analytics Request / Response
# ---------------------------------------------------------------------------


class AnalyticsRequest(BaseSchema):
    """Request body for triggering analytics pipeline operations.

    Attributes:
        operation: Pipeline operation to execute.
        video_id: Optional video identifier to scope the analytics.
        date_from: Optional start date for filtering (YYYY-MM-DD).
        date_to: Optional end date for filtering (YYYY-MM-DD).
        metrics: Optional list of specific metric names to compute.

    Example:
        .. code-block:: json

            {
                "operation": "full_pipeline",
                "video_id": "vid_001",
                "date_from": "2025-01-01",
                "date_to": "2025-01-31"
            }
    """

    operation: Annotated[
        PipelineOperation,
        Field(
            default=PipelineOperation.FULL_PIPELINE,
            description="Pipeline operation to execute.",
        ),
    ] = PipelineOperation.FULL_PIPELINE
    video_id: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description="Optional video identifier to scope analytics.",
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
    metrics: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="Optional list of metric names to compute.",
        ),
    ] = None

    @field_validator("operation", mode="before")
    @classmethod
    def _coerce_operation(cls, value: str | PipelineOperation) -> PipelineOperation:
        """Coerce raw operation strings into the :class:`PipelineOperation` enum."""
        if isinstance(value, PipelineOperation):
            return value
        try:
            return PipelineOperation(value.strip().lower().replace(" ", "_"))
        except ValueError:
            valid = ", ".join(sorted(o.value for o in PipelineOperation))
            raise ValueError(
                f"Invalid operation '{value}'. Valid: {valid}."
            ) from None

    @field_validator("metrics")
    @classmethod
    def _validate_metrics(
        cls, value: list[str] | None
    ) -> list[str] | None:
        """Validate and normalize metric names."""
        if value is None:
            return None
        normalized: list[str] = []
        for metric in value:
            stripped = metric.strip().lower()
            if not stripped:
                raise ValueError("metrics entries must not be empty.")
            if stripped not in _VALID_METRICS:
                valid = ", ".join(sorted(_VALID_METRICS))
                raise ValueError(
                    f"Invalid metric '{metric}'. Valid: {valid}."
                )
            normalized.append(stripped)
        return normalized


class AnalyticsResponse(BaseSchema):
    """Response payload for an analytics pipeline execution.

    Mirrors the shape returned by
    :meth:`AnalyticsService.run_pipeline
    <backend.services.analytics_service.AnalyticsService.run_pipeline>`.

    Attributes:
        operation: The operation that was executed.
        status: Execution status (``"completed"``, ``"failed"``).
        aggregation: Optional aggregation results.
        kpis: Optional KPI results.
        spoilage_metrics: Optional spoilage metrics.
        freshness_metrics: Optional freshness metrics.
        message: Optional status message.
    """

    operation: Annotated[
        str,
        Field(description="The operation that was executed."),
    ]
    status: Annotated[
        str,
        Field(
            pattern=r"^(completed|failed|running)$",
            description="Execution status.",
            examples=["completed"],
        ),
    ]
    aggregation: Annotated[
        dict[str, object] | None,
        Field(
            default=None,
            description="Optional aggregation results.",
        ),
    ] = None
    kpis: Annotated[
        dict[str, object] | None,
        Field(
            default=None,
            description="Optional KPI results.",
        ),
    ] = None
    spoilage_metrics: Annotated[
        dict[str, object] | None,
        Field(
            default=None,
            description="Optional spoilage metrics.",
        ),
    ] = None
    freshness_metrics: Annotated[
        dict[str, object] | None,
        Field(
            default=None,
            description="Optional freshness metrics.",
        ),
    ] = None
    message: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional status message.",
        ),
    ] = None

    @field_validator("operation")
    @classmethod
    def _operation_not_empty(cls, value: str) -> str:
        """Reject empty operation identifiers."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("operation must not be empty.")
        return stripped

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        """Normalize status to lowercase."""
        normalized = value.strip().lower()
        if normalized not in ("completed", "failed", "running"):
            raise ValueError(
                f"Invalid status '{value}'. Must be one of: "
                f"completed, failed, running."
            )
        return normalized


# ---------------------------------------------------------------------------
# KPI
# ---------------------------------------------------------------------------


class KPIResponse(BaseSchema):
    """A single KPI metric record.

    Attributes:
        metric: KPI metric name.
        value: Numeric value of the metric.
        unit: Optional unit label (e.g. ``"count"``, ``"percent"``).
        timestamp: ISO-8601 timestamp when the KPI was computed.
        video_id: Optional video identifier the KPI scopes to.
    """

    metric: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="KPI metric name.",
            examples=["total_detections"],
        ),
    ]
    value: Annotated[
        float,
        Field(description="Numeric value of the metric.", examples=[42.0]),
    ]
    unit: Annotated[
        str | None,
        Field(
            default=None,
            max_length=50,
            description="Optional unit label.",
            examples=["count"],
        ),
    ] = None
    timestamp: Annotated[
        datetime,
        Field(description="ISO-8601 computation timestamp."),
    ]
    video_id: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description="Optional scoped video identifier.",
        ),
    ] = None

    @field_validator("metric")
    @classmethod
    def _validate_metric_name(cls, value: str) -> str:
        """Reject empty metric names."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("metric name must not be empty.")
        return stripped

    @field_validator("timestamp", mode="before")
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
# Dashboard Metrics
# ---------------------------------------------------------------------------


class DashboardMetrics(BaseSchema):
    """Top-level metrics aggregated for dashboard display.

    Attributes:
        total_videos: Total number of videos processed.
        total_detections: Total number of detections.
        total_alerts: Total number of alerts generated.
        total_events: Total number of events recorded.
        average_confidence: Overall average detection confidence.
        spoilage_risk_index: Global spoilage risk index (0.0–1.0).
        freshness_score: Global freshness score (0–100).
        period_days: Number of days the metrics cover.
    """

    total_videos: Annotated[
        int,
        Field(ge=0, default=0, description="Total videos processed."),
    ] = 0
    total_detections: Annotated[
        int,
        Field(ge=0, default=0, description="Total detections."),
    ] = 0
    total_alerts: Annotated[
        int,
        Field(ge=0, default=0, description="Total alerts generated."),
    ] = 0
    total_events: Annotated[
        int,
        Field(ge=0, default=0, description="Total events recorded."),
    ] = 0
    average_confidence: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.0,
            description="Average detection confidence (0.0–1.0).",
        ),
    ] = 0.0
    spoilage_risk_index: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.0,
            description="Global spoilage risk index (0.0–1.0).",
        ),
    ] = 0.0
    freshness_score: Annotated[
        float,
        Field(
            ge=0.0,
            le=100.0,
            default=100.0,
            description="Global freshness score (0–100).",
        ),
    ] = 100.0
    period_days: Annotated[
        int,
        Field(
            ge=1,
            default=7,
            description="Number of days the metrics cover.",
        ),
    ] = 7

    @field_validator("average_confidence", "spoilage_risk_index")
    @classmethod
    def _validate_zero_to_one(cls, value: float) -> float:
        """Ensure values are in [0.0, 1.0]."""
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"Value must be between 0.0 and 1.0, got {value}.")
        return value

    @field_validator("freshness_score")
    @classmethod
    def _validate_freshness(cls, value: float) -> float:
        """Ensure freshness score is in [0.0, 100.0]."""
        if not (0.0 <= value <= 100.0):
            raise ValueError(f"Freshness score must be between 0 and 100, got {value}.")
        return value


# ---------------------------------------------------------------------------
# Trend Response
# ---------------------------------------------------------------------------


class TrendPoint(BaseSchema):
    """A single data point in a time-series trend.

    Attributes:
        date: Date of the data point (YYYY-MM-DD).
        value: Numeric value at that date.
    """

    date: Annotated[
        str,
        Field(
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            description="Date in YYYY-MM-DD format.",
        ),
    ]
    value: Annotated[
        float,
        Field(ge=0.0, description="Numeric value at the date."),
    ]


class TrendResponse(BaseSchema):
    """Time-series trend response.

    Attributes:
        metric: The metric name the trend describes.
        data_points: Chronological list of trend data points.
        period_days: Number of days the trend covers.
        average: Average value over the period.
        minimum: Minimum value over the period.
        maximum: Maximum value over the period.
    """

    metric: Annotated[
        str,
        Field(
            min_length=1,
            description="The metric name the trend describes.",
            examples=["total_detections"],
        ),
    ]
    data_points: Annotated[
        list[TrendPoint],
        Field(
            default_factory=list,
            description="Chronological trend data points.",
        ),
    ]
    period_days: Annotated[
        int,
        Field(ge=1, default=7, description="Number of days covered."),
    ] = 7
    average: Annotated[
        float,
        Field(default=0.0, description="Average value over the period."),
    ] = 0.0
    minimum: Annotated[
        float,
        Field(default=0.0, description="Minimum value over the period."),
    ] = 0.0
    maximum: Annotated[
        float,
        Field(default=0.0, description="Maximum value over the period."),
    ] = 0.0

    @field_validator("metric")
    @classmethod
    def _validate_metric(cls, value: str) -> str:
        """Reject empty metric names."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("metric must not be empty.")
        return stripped


# ---------------------------------------------------------------------------
# Spoilage Metrics
# ---------------------------------------------------------------------------


class RiskFactor(BaseSchema):
    """A named spoilage risk factor with its contribution level.

    Attributes:
        factor: Factor name.
        contribution: Contribution level (0.0–1.0).
        description: Optional description of the factor.
    """

    factor: Annotated[
        str,
        Field(min_length=1, description="Risk factor name."),
    ]
    contribution: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description="Contribution level (0.0–1.0).",
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            default=None,
            max_length=500,
            description="Optional description.",
        ),
    ] = None


class SpoilageMetrics(BaseSchema):
    """Spoilage risk assessment metrics.

    Attributes:
        spoilage_risk_index: Overall spoilage risk index (0.0–1.0).
        high_risk_detections: Count of high-risk detections.
        risk_factors: Contributing risk factors.
        timestamp: ISO-8601 computation timestamp.
    """

    spoilage_risk_index: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.0,
            description="Overall spoilage risk index (0.0–1.0).",
        ),
    ] = 0.0
    high_risk_detections: Annotated[
        int,
        Field(
            ge=0,
            default=0,
            description="Count of high-risk detections.",
        ),
    ] = 0
    risk_factors: Annotated[
        list[RiskFactor],
        Field(
            default_factory=list,
            description="Contributing risk factors.",
        ),
    ]
    timestamp: Annotated[
        datetime,
        Field(description="ISO-8601 computation timestamp."),
    ]

    @field_validator("timestamp", mode="before")
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
# Freshness Metrics
# ---------------------------------------------------------------------------


class FreshnessMetrics(BaseSchema):
    """Freshness and turnover analysis metrics.

    Attributes:
        freshness_score: Overall freshness score (0–100).
        turnover_rate: Inventory turnover rate.
        stale_detection_ratio: Ratio of stale detections (0.0–1.0).
        avg_storage_duration_hours: Average storage duration in hours.
        timestamp: ISO-8601 computation timestamp.
    """

    freshness_score: Annotated[
        float,
        Field(
            ge=0.0,
            le=100.0,
            default=100.0,
            description="Overall freshness score (0–100).",
        ),
    ] = 100.0
    turnover_rate: Annotated[
        float,
        Field(
            ge=0.0,
            default=0.0,
            description="Inventory turnover rate.",
        ),
    ] = 0.0
    stale_detection_ratio: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.0,
            description="Ratio of stale detections (0.0–1.0).",
        ),
    ] = 0.0
    avg_storage_duration_hours: Annotated[
        float,
        Field(
            ge=0.0,
            default=0.0,
            description="Average storage duration in hours.",
        ),
    ] = 0.0
    timestamp: Annotated[
        datetime,
        Field(description="ISO-8601 computation timestamp."),
    ]

    @field_validator("timestamp", mode="before")
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
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "AnalyticsRequest",
    "AnalyticsResponse",
    "KPIResponse",
    "DashboardMetrics",
    "TrendResponse",
    "TrendPoint",
    "SpoilageMetrics",
    "RiskFactor",
    "FreshnessMetrics",
]

