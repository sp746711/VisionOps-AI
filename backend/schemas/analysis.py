"""VisionOps AI — Analysis Domain Schemas.

Pydantic v2 schemas for detection analysis, results aggregation, and
detection statistics. These map directly to the interfaces exposed by
:mod:`backend.services.analysis_service` and the analysis API endpoints.

Contents:
    - :class:`DetectionSchema` — a single validated detection record.
    - :class:`DetectionSummary` — aggregated detection summary for a video.
    - :class:`DetectionStatistics` — detection statistics for the dashboard.
    - :class:`AnalysisRequest` — request body for running detection analysis.
    - :class:`AnalysisResponse` — response payload for an analysis run.

Validation covers required fields, confidence values (0.0–1.0),
bounding-box integrity, frame numbers, class names, and video identifiers.

Usage:
    from backend.schemas.analysis import (
        DetectionSchema, DetectionSummary, DetectionStatistics,
        AnalysisRequest, AnalysisResponse,
    )
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from backend.schemas.common import BaseSchema, BoundingBox, DetectionClass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DETECTION_ID_PREFIX: str = "det_"
_VIDEO_ID_PREFIX: str = "vid_"


# ---------------------------------------------------------------------------
# Detection Schema
# ---------------------------------------------------------------------------


class DetectionSchema(BaseSchema):
    """A single validated detection record.

    Attributes:
        detection_id: Unique detection identifier (``det_...``).
        video_id: Video the detection belongs to (``vid_...``).
        frame_number: Frame index where the object was detected.
        class_name: Detected object class name.
        confidence: Detection confidence score in ``[0.0, 1.0]``.
        bbox: Normalized bounding box.
        track_id: Optional object tracking identifier.
        created_at: ISO-8601 creation timestamp.
    """

    detection_id: Annotated[
        str,
        Field(
            min_length=1,
            description="Unique detection identifier (prefix 'det_').",
            examples=["det_001"],
        ),
    ]
    video_id: Annotated[
        str,
        Field(
            min_length=1,
            description="Video identifier (prefix 'vid_').",
            examples=["vid_001"],
        ),
    ]
    frame_number: Annotated[
        int,
        Field(
            ge=0,
            description="Frame index where the object was detected.",
            examples=[1],
        ),
    ]
    class_name: Annotated[
        str | DetectionClass,
        Field(
            min_length=1,
            max_length=100,
            description="Detected object class name.",
            examples=["person"],
        ),
    ]
    confidence: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            description="Detection confidence score (0.0–1.0).",
            examples=[0.95],
        ),
    ]
    bbox: Annotated[
        BoundingBox,
        Field(description="Normalized bounding box of the detection."),
    ]
    track_id: Annotated[
        str | None,
        Field(
            default=None,
            max_length=100,
            description="Optional object tracking identifier.",
        ),
    ] = None
    created_at: Annotated[
        datetime,
        Field(description="ISO-8601 creation timestamp."),
    ]

    @field_validator("detection_id")
    @classmethod
    def _validate_detection_id(cls, value: str) -> str:
        """Validate the detection identifier prefix and non-emptiness."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("detection_id must not be empty.")
        if not stripped.startswith(_DETECTION_ID_PREFIX):
            raise ValueError(
                f"detection_id must start with '{_DETECTION_ID_PREFIX}'."
            )
        return stripped

    @field_validator("video_id")
    @classmethod
    def _validate_video_id(cls, value: str) -> str:
        """Validate the video identifier prefix and non-emptiness."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("video_id must not be empty.")
        if not stripped.startswith(_VIDEO_ID_PREFIX):
            raise ValueError(
                f"video_id must start with '{_VIDEO_ID_PREFIX}'."
            )
        return stripped

    @field_validator("class_name", mode="before")
    @classmethod
    def _coerce_class_name(cls, value: str | DetectionClass) -> str:
        """Normalize the class name to a lowercase string."""
        if isinstance(value, DetectionClass):
            return value.value
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("class_name must not be empty.")
        return normalized

    @field_validator("confidence")
    @classmethod
    def _validate_confidence(cls, value: float) -> float:
        """Guard confidence against out-of-range values."""
        if not (0.0 <= value <= 1.0):
            raise ValueError(
                f"confidence must be between 0.0 and 1.0, got {value}."
            )
        return value

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

    @model_validator(mode="after")
    def _validate_track_id_consistency(self) -> "DetectionSchema":
        """Enforce optional consistency rules across fields."""
        return self


# ---------------------------------------------------------------------------
# Detection Summary
# ---------------------------------------------------------------------------


class DetectionSummary(BaseSchema):
    """Aggregated detection summary for a single video.

    Mirrors the shape returned by
    :meth:`AnalysisService.aggregate_results
    <backend.services.analysis_service.AnalysisService.aggregate_results>`.

    Attributes:
        video_id: The video identifier.
        total_detections: Total detection count.
        unique_classes: Number of distinct object classes.
        class_counts: Per-class detection counts.
        average_confidence: Overall average confidence score.
        class_avg_confidence: Per-class average confidence.
        detections_per_frame: Average detections per frame.
    """

    video_id: Annotated[
        str,
        Field(min_length=1, description="The video identifier."),
    ]
    total_detections: Annotated[
        int,
        Field(ge=0, description="Total detection count."),
    ]
    unique_classes: Annotated[
        int,
        Field(ge=0, description="Number of distinct object classes."),
    ]
    class_counts: Annotated[
        dict[str, int],
        Field(
            default_factory=dict,
            description="Per-class detection counts.",
        ),
    ]
    average_confidence: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.0,
            description="Overall average confidence score.",
        ),
    ]
    class_avg_confidence: Annotated[
        dict[str, float],
        Field(
            default_factory=dict,
            description="Per-class average confidence.",
        ),
    ]
    detections_per_frame: Annotated[
        float,
        Field(
            ge=0.0,
            default=0.0,
            description="Average detections per frame.",
        ),
    ]

    @field_validator("video_id")
    @classmethod
    def _validate_video_id_present(cls, value: str) -> str:
        """Reject empty video identifiers."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("video_id must not be empty.")
        return stripped

    @field_validator("class_counts")
    @classmethod
    def _validate_class_counts(cls, value: dict[str, int]) -> dict[str, int]:
        """Ensure class counts are non-negative."""
        for class_name, count in value.items():
            if count < 0:
                raise ValueError(
                    f"class_counts[{class_name!r}] must be >= 0, got {count}."
                )
        return value

    @field_validator("class_avg_confidence")
    @classmethod
    def _validate_class_avg_confidence(
        cls, value: dict[str, float]
    ) -> dict[str, float]:
        """Ensure per-class average confidence is in range."""
        for class_name, avg in value.items():
            if not (0.0 <= avg <= 1.0):
                raise ValueError(
                    f"class_avg_confidence[{class_name!r}] must be between "
                    f"0.0 and 1.0, got {avg}."
                )
        return value


# ---------------------------------------------------------------------------
# Detection Statistics (sub-types)
# ---------------------------------------------------------------------------


class ConfidenceDistribution(BaseSchema):
    """Binned confidence distribution for detection statistics.

    Attributes:
        low: Count of detections with confidence < 0.3.
        medium: Count with confidence in [0.3, 0.7).
        high: Count with confidence >= 0.7.
    """

    low: Annotated[
        int,
        Field(ge=0, description="Count with confidence < 0.3."),
    ] = 0
    medium: Annotated[
        int,
        Field(ge=0, description="Count with confidence in [0.3, 0.7)."),
    ] = 0
    high: Annotated[
        int,
        Field(ge=0, description="Count with confidence >= 0.7."),
    ] = 0


class ClassCount(BaseSchema):
    """A class name paired with its detection count.

    Attributes:
        class_name: Detected object class name.
        count: Detection count for the class.
    """

    class_name: Annotated[
        str,
        Field(min_length=1, description="Detected object class name."),
    ]
    count: Annotated[
        int,
        Field(ge=0, description="Detection count."),
    ]


class TimePoint(BaseSchema):
    """A single (date, count) point for a time-series.

    Attributes:
        date: The date in ``YYYY-MM-DD`` format.
        count: The count for that date.
    """

    date: Annotated[
        str,
        Field(
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            description="Date in YYYY-MM-DD format.",
        ),
    ]
    count: Annotated[
        int,
        Field(ge=0, description="Count for the date."),
    ]


# ---------------------------------------------------------------------------
# Detection Statistics
# ---------------------------------------------------------------------------


class DetectionStatistics(BaseSchema):
    """Detection statistics returned to dashboard and analysis consumers.

    Mirrors the shape returned by
    :meth:`DashboardService.get_detection_stats
    <backend.services.dashboard_service.DashboardService.get_detection_stats>`.

    Attributes:
        total_detections: Total detection count.
        unique_classes: Number of distinct object classes.
        average_confidence: Mean confidence score.
        top_classes: Most frequent classes.
        confidence_distribution: Binned confidence counts.
        detections_over_time: Detection counts by date.
    """

    total_detections: Annotated[
        int,
        Field(ge=0, description="Total detection count."),
    ] = 0
    unique_classes: Annotated[
        int,
        Field(ge=0, description="Number of distinct object classes."),
    ] = 0
    average_confidence: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.0,
            description="Mean confidence score.",
        ),
    ] = 0.0
    top_classes: Annotated[
        list[ClassCount],
        Field(
            default_factory=list,
            description="Most frequent classes (ranked).",
        ),
    ]
    confidence_distribution: Annotated[
        ConfidenceDistribution,
        Field(
            default=ConfidenceDistribution(),
            description="Binned confidence counts.",
        ),
    ]
    detections_over_time: Annotated[
        list[TimePoint],
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


# ---------------------------------------------------------------------------
# Analysis Request / Response
# ---------------------------------------------------------------------------


class AnalysisRequest(BaseSchema):
    """Request body for running detection analysis on a video.

    Attributes:
        video_id: Unique video identifier (``vid_...``).
        detections: List of raw detection dictionaries as produced by
            AI inference. Each dict should contain ``class_name``,
            ``confidence``, and ``bbox`` keys.
        source_frame: Optional frame number this batch came from.
        min_confidence: Optional minimum confidence threshold.
        allowed_classes: Optional list of allowed class names.

    Example:
        .. code-block:: json

            {
                "video_id": "vid_001",
                "detections": [
                    {
                        "class_name": "person",
                        "confidence": 0.95,
                        "bbox": [100, 200, 50, 100]
                    }
                ],
                "source_frame": 1
            }
    """

    video_id: Annotated[
        str,
        Field(
            min_length=1,
            description="Unique video identifier (prefix 'vid_').",
            examples=["vid_001"],
        ),
    ]
    detections: Annotated[
        list[dict[str, object]],
        Field(
            description=(
                "Raw detection dictionaries from AI inference "
                "(class_name, confidence, bbox)."
            ),
        ),
    ]
    source_frame: Annotated[
        int | None,
        Field(
            default=None,
            ge=0,
            description="Optional source frame number.",
        ),
    ] = None
    min_confidence: Annotated[
        float | None,
        Field(
            default=None,
            ge=0.0,
            le=1.0,
            description="Optional minimum confidence threshold.",
        ),
    ] = None
    allowed_classes: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="Optional list of allowed class names.",
        ),
    ] = None

    @field_validator("video_id")
    @classmethod
    def _validate_video_id(cls, value: str) -> str:
        """Validate the video identifier prefix and non-emptiness."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("video_id must not be empty.")
        if not stripped.startswith(_VIDEO_ID_PREFIX):
            raise ValueError(
                f"video_id must start with '{_VIDEO_ID_PREFIX}'."
            )
        return stripped

    @field_validator("detections")
    @classmethod
    def _validate_detections_list(cls, value: list[dict[str, object]]) -> list[dict[str, object]]:
        """Ensure the detections payload is a list of non-empty dicts."""
        if not value:
            raise ValueError("detections must not be empty.")
        for idx, det in enumerate(value):
            if not isinstance(det, dict) or not det:
                raise ValueError(
                    f"detections[{idx}] must be a non-empty dict."
                )
        return value

    @field_validator("allowed_classes")
    @classmethod
    def _validate_allowed_classes(
        cls, value: list[str] | None
    ) -> list[str] | None:
        """Normalize allowed class names to lowercase stripped strings."""
        if value is None:
            return None
        normalized: list[str] = []
        for allowed_class in value:
            stripped = allowed_class.strip().lower()
            if not stripped:
                raise ValueError("allowed_classes entries must not be empty.")
            normalized.append(stripped)
        return normalized


class AnalysisResponse(BaseSchema):
    """Response payload for an analysis run.

    Attributes:
        video_id: The analyzed video identifier.
        total_detections: Number of persisted detections.
        detections: The enriched, validated detection records.
        summary: Optional aggregated :class:`DetectionSummary`.
        message: Optional status message.
    """

    video_id: Annotated[
        str,
        Field(min_length=1, description="The analyzed video identifier."),
    ]
    total_detections: Annotated[
        int,
        Field(ge=0, description="Number of persisted detections."),
    ]
    detections: Annotated[
        list[DetectionSchema],
        Field(
            default_factory=list,
            description="Enriched, validated detection records.",
        ),
    ]
    summary: Annotated[
        DetectionSummary | None,
        Field(
            default=None,
            description="Optional aggregated summary.",
        ),
    ] = None
    message: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional status message.",
        ),
    ] = None

    @field_validator("video_id")
    @classmethod
    def _validate_video_id_present(cls, value: str) -> str:
        """Reject empty video identifiers."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("video_id must not be empty.")
        return stripped


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "DetectionSchema",
    "DetectionSummary",
    "DetectionStatistics",
    "ConfidenceDistribution",
    "ClassCount",
    "TimePoint",
    "AnalysisRequest",
    "AnalysisResponse",
]

