"""VisionOps AI — Dashboard Domain Schemas.

Pydantic v2 schemas for the dashboard summary, statistics, alerts, and
performance metrics. These map directly to the interfaces exposed by
:mod:`backend.services.dashboard_service` and the dashboard API.

Contents:
    - :class:`DashboardSummary` — overall dashboard counts.
    - :class:`DashboardStats` — alias for :class:`DashboardStatistics`.
    - :class:`DashboardStatistics` — detection statistics for the dashboard.
    - :class:`AlertSummary` — aggregated alert data.
    - :class:`RecentVideo` — a recent video summary.
    - :class:`PerformanceMetrics` — processing performance data.
    - :class:`DashboardResponse` — full dashboard payload.

Validation covers required fields, enum values, numeric ranges, video
and alert identifiers, and date formatting.

Usage:
    from backend.schemas.dashboard import (
        DashboardSummary, DashboardStatistics, DashboardStats,
        AlertSummary, RecentVideo, PerformanceMetrics, DashboardResponse,
    )
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import Field, field_validator

from backend.schemas.common import BaseSchema, Severity, VideoStatus


# ---------------------------------------------------------------------------
# Dashboard Summary
# ---------------------------------------------------------------------------


class VideosByStatus(BaseSchema):
    """Breakdown of videos grouped by their lifecycle status.

    Attributes:
        uploaded: Count of uploaded videos.
        queued: Count of queued videos.
        processing: Count of processing videos.
        completed: Count of completed videos.
        failed: Count of failed videos.
        cancelled: Count of cancelled videos.
    """

    uploaded: Annotated[int, Field(ge=0, default=0)] = 0
    queued: Annotated[int, Field(ge=0, default=0)] = 0
    processing: Annotated[int, Field(ge=0, default=0)] = 0
    completed: Annotated[int, Field(ge=0, default=0)] = 0
    failed: Annotated[int, Field(ge=0, default=0)] = 0
    cancelled: Annotated[int, Field(ge=0, default=0)] = 0


class DashboardSummary(BaseSchema):
    """Overall dashboard summary counts.

    Mirrors the shape returned by
    :meth:`DashboardService.get_summary
    <backend.services.dashboard_service.DashboardService.get_summary>`.

    Attributes:
        total_videos: Total number of uploaded videos.
        total_detections: Total detection count.
        total_events: Total event count.
        total_alerts: Total alert count.
        total_kpis: Total KPI count.
        videos_by_status: Videos grouped by status.
    """

    total_videos: Annotated[
        int,
        Field(ge=0, default=0, description="Total uploaded videos."),
    ] = 0
    total_detections: Annotated[
        int,
        Field(ge=0, default=0, description="Total detection count."),
    ] = 0
    total_events: Annotated[
        int,
        Field(ge=0, default=0, description="Total event count."),
    ] = 0
    total_alerts: Annotated[
        int,
        Field(ge=0, default=0, description="Total alert count."),
    ] = 0
    total_kpis: Annotated[
        int,
        Field(ge=0, default=0, description="Total KPI count."),
    ] = 0
    videos_by_status: Annotated[
        VideosByStatus,
        Field(
            default_factory=VideosByStatus,
            description="Videos grouped by lifecycle status.",
        ),
    ]


# ---------------------------------------------------------------------------
# Alert Summary
# ---------------------------------------------------------------------------


class AlertSeverityCount(BaseSchema):
    """Breakdown of alerts by severity level.

    Attributes:
        low: Count of low-severity alerts.
        medium: Count of medium-severity alerts.
        high: Count of high-severity alerts.
        critical: Count of critical-severity alerts.
    """

    low: Annotated[int, Field(ge=0, default=0)] = 0
    medium: Annotated[int, Field(ge=0, default=0)] = 0
    high: Annotated[int, Field(ge=0, default=0)] = 0
    critical: Annotated[int, Field(ge=0, default=0)] = 0


class RecentAlert(BaseSchema):
    """A single recent alert with key details.

    Attributes:
        alert_id: Unique alert identifier.
        severity: Alert severity level.
        message: Alert message.
        created_at: ISO-8601 creation timestamp.
        video_id: Optional associated video identifier.
    """

    alert_id: Annotated[
        str,
        Field(min_length=1, description="Unique alert identifier."),
    ]
    severity: Annotated[
        Severity,
        Field(description="Alert severity level."),
    ]
    message: Annotated[
        str,
        Field(min_length=1, max_length=1000, description="Alert message."),
    ]
    created_at: Annotated[
        datetime,
        Field(description="ISO-8601 creation timestamp."),
    ]
    video_id: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            description="Optional associated video identifier.",
        ),
    ] = None

    @field_validator("alert_id")
    @classmethod
    def _alert_id_not_empty(cls, value: str) -> str:
        """Reject empty alert identifiers."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("alert_id must not be empty.")
        return stripped

    @field_validator("severity", mode="before")
    @classmethod
    def _coerce_severity(cls, value: str | Severity) -> Severity:
        """Coerce raw severity strings into the :class:`Severity` enum."""
        if isinstance(value, Severity):
            return value
        try:
            return Severity(value.strip().lower())
        except ValueError:
            valid = ", ".join(sorted(s.value for s in Severity))
            raise ValueError(
                f"Invalid severity '{value}'. Valid: {valid}."
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


class AlertSummary(BaseSchema):
    """Aggregated alert summary.

    Mirrors the shape returned by
    :meth:`DashboardService.get_alert_summary
    <backend.services.dashboard_service.DashboardService.get_alert_summary>`.

    Attributes:
        total_alerts: Total alert count.
        by_severity: Alerts grouped by severity.
        recent_alerts: Most recent alerts.
    """

    total_alerts: Annotated[
        int,
        Field(ge=0, default=0, description="Total alert count."),
    ] = 0
    by_severity: Annotated[
        AlertSeverityCount,
        Field(
            default_factory=AlertSeverityCount,
            description="Alerts grouped by severity.",
        ),
    ]
    recent_alerts: Annotated[
        list[RecentAlert],
        Field(
            default_factory=list,
            description="Most recent alerts.",
        ),
    ]


# ---------------------------------------------------------------------------
# Recent Video
# ---------------------------------------------------------------------------


class RecentVideo(BaseSchema):
    """A summary of a recently processed video.

    Attributes:
        video_id: Unique video identifier.
        filename: Original filename.
        status: Lifecycle status.
        duration_seconds: Video duration.
        total_detections: Detection count.
        created_at: ISO-8601 creation timestamp.
        thumbnail_path: Optional thumbnail path.
    """

    video_id: Annotated[
        str,
        Field(min_length=1, description="Unique video identifier."),
    ]
    filename: Annotated[
        str,
        Field(min_length=1, max_length=255, description="Original filename."),
    ]
    status: Annotated[
        VideoStatus,
        Field(description="Lifecycle status."),
    ]
    duration_seconds: Annotated[
        float,
        Field(ge=0.0, default=0.0, description="Video duration in seconds."),
    ] = 0.0
    total_detections: Annotated[
        int,
        Field(ge=0, default=0, description="Detection count for the video."),
    ] = 0
    created_at: Annotated[
        datetime,
        Field(description="ISO-8601 creation timestamp."),
    ]
    thumbnail_path: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional thumbnail file path.",
        ),
    ] = None

    @field_validator("video_id", "filename")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        """Reject empty string fields."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field must not be empty.")
        return stripped

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, value: str | VideoStatus) -> VideoStatus:
        """Coerce raw status strings into the :class:`VideoStatus` enum."""
        if isinstance(value, VideoStatus):
            return value
        try:
            return VideoStatus(value.strip().lower())
        except ValueError:
            valid = ", ".join(sorted(s.value for s in VideoStatus))
            raise ValueError(
                f"Invalid status '{value}'. Valid: {valid}."
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
# Dashboard Statistics
# ---------------------------------------------------------------------------


class DashboardStatistics(BaseSchema):
    """Detection and performance statistics for the dashboard.

    Mirrors the shape returned by
    :meth:`DashboardService.get_detection_stats
    <backend.services.dashboard_service.DashboardService.get_detection_stats>`.

    Attributes:
        total_detections: Total detection count.
        unique_classes: Number of distinct object classes.
        average_confidence: Mean confidence score.
        top_classes: Ranked top class names with counts.
        confidence_distribution: Binned confidence counts.
        detections_over_time: Detection counts by date.
    """

    total_detections: Annotated[
        int,
        Field(ge=0, default=0, description="Total detection count."),
    ] = 0
    unique_classes: Annotated[
        int,
        Field(ge=0, default=0, description="Distinct object classes."),
    ] = 0
    average_confidence: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.0,
            description="Mean confidence score (0.0–1.0).",
        ),
    ] = 0.0
    top_classes: Annotated[
        list[dict[str, object]],
        Field(
            default_factory=list,
            description="Ranked top class names with counts.",
        ),
    ]
    confidence_distribution: Annotated[
        dict[str, int],
        Field(
            default_factory=dict,
            description="Binned confidence counts.",
        ),
    ]
    detections_over_time: Annotated[
        list[dict[str, object]],
        Field(
            default_factory=list,
            description="Detection counts by date.",
        ),
    ]

    @field_validator("average_confidence")
    @classmethod
    def _validate_avg_confidence(cls, value: float) -> float:
        """Guard average confidence against out-of-range values."""
        if not (0.0 <= value <= 1.0):
            raise ValueError(
                f"average_confidence must be between 0.0 and 1.0, "
                f"got {value}."
            )
        return value


# Backward-compatible alias used by the test suite.
DashboardStats = DashboardStatistics


# ---------------------------------------------------------------------------
# Performance Metrics
# ---------------------------------------------------------------------------


class PerformanceMetrics(BaseSchema):
    """Processing performance metrics.

    Mirrors the shape returned by
    :meth:`DashboardService.get_performance_metrics
    <backend.services.dashboard_service.DashboardService.get_performance_metrics>`.

    Attributes:
        period_days: Number of days the metrics cover.
        videos_processed: Videos processed in the period.
        processing_success_rate: Success rate (0.0–1.0).
        average_processing_time: Average processing time in seconds.
        total_processing_time: Total processing time in seconds.
        longest_processing_time: Longest single processing time.
        shortest_processing_time: Shortest single processing time.
    """

    period_days: Annotated[
        int,
        Field(ge=1, default=7, description="Period in days."),
    ] = 7
    videos_processed: Annotated[
        int,
        Field(ge=0, default=0, description="Videos processed."),
    ] = 0
    processing_success_rate: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.0,
            description="Success rate (0.0–1.0).",
        ),
    ] = 0.0
    average_processing_time: Annotated[
        float,
        Field(
            ge=0.0,
            default=0.0,
            description="Average processing time in seconds.",
        ),
    ] = 0.0
    total_processing_time: Annotated[
        float,
        Field(
            ge=0.0,
            default=0.0,
            description="Total processing time in seconds.",
        ),
    ] = 0.0
    longest_processing_time: Annotated[
        float,
        Field(
            ge=0.0,
            default=0.0,
            description="Longest processing time in seconds.",
        ),
    ] = 0.0
    shortest_processing_time: Annotated[
        float,
        Field(
            ge=0.0,
            default=0.0,
            description="Shortest processing time in seconds.",
        ),
    ] = 0.0


# ---------------------------------------------------------------------------
# Dashboard Response
# ---------------------------------------------------------------------------


class DashboardResponse(BaseSchema):
    """Complete dashboard response payload.

    Aggregates the summary, statistics, alert summary, recent videos,
    and performance metrics into a single response.

    Attributes:
        summary: Overall dashboard summary counts.
        statistics: Detection and class statistics.
        alert_summary: Alert summary data.
        recent_videos: List of recently processed videos.
        performance_metrics: Performance metrics.
        spoilage_risk_index: Current spoilage risk index (0.0–1.0).
        freshness_score: Current freshness score (0–100).
    """

    summary: Annotated[
        DashboardSummary,
        Field(description="Overall dashboard summary counts."),
    ]
    statistics: Annotated[
        DashboardStatistics,
        Field(description="Detection and class statistics."),
    ]
    alert_summary: Annotated[
        AlertSummary,
        Field(description="Alert summary data."),
    ]
    recent_videos: Annotated[
        list[RecentVideo],
        Field(
            default_factory=list,
            description="Recently processed videos.",
        ),
    ]
    performance_metrics: Annotated[
        PerformanceMetrics,
        Field(description="Processing performance metrics."),
    ]
    spoilage_risk_index: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.0,
            description="Current spoilage risk index (0.0–1.0).",
        ),
    ] = 0.0
    freshness_score: Annotated[
        float,
        Field(
            ge=0.0,
            le=100.0,
            default=100.0,
            description="Current freshness score (0–100).",
        ),
    ] = 100.0

    @field_validator("spoilage_risk_index")
    @classmethod
    def _validate_risk_index(cls, value: float) -> float:
        """Ensure spoilage risk index is in [0.0, 1.0]."""
        if not (0.0 <= value <= 1.0):
            raise ValueError(
                f"spoilage_risk_index must be between 0.0 and 1.0, "
                f"got {value}."
            )
        return value

    @field_validator("freshness_score")
    @classmethod
    def _validate_freshness(cls, value: float) -> float:
        """Ensure freshness score is in [0.0, 100.0]."""
        if not (0.0 <= value <= 100.0):
            raise ValueError(
                f"freshness_score must be between 0 and 100, got {value}."
            )
        return value


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "DashboardSummary",
    "DashboardStatistics",
    "DashboardStats",
    "AlertSummary",
    "RecentVideo",
    "PerformanceMetrics",
    "DashboardResponse",
    "VideosByStatus",
    "AlertSeverityCount",
    "RecentAlert",
]

