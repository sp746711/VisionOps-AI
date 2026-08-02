"""VisionOps AI — Analytics Data Transformation.

This module implements the analytics transformation layer.  It converts
cleaned analytics source records into analytical structures:

* detection → analytical record (with flattened bounding-box columns),
* class/category normalization,
* timestamp/date extraction,
* frame/time conversion,
* tracking statistics,
* per-video transformation,
* derived analytical columns.

Design rules:

* Only derived values that are required by the existing
  :class:`AnalyticsService`, :class:`DashboardService`,
  :class:`ReportService`, Power BI dataset contract, and
  business/data schemas are produced.
* All transforms are deterministic.
* Empty inputs produce safe default outputs (``0``, ``[]``, ``{}``).
* Public outputs are plain Python ``int``/``float`` values (NumPy
  scalars are normalised).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Any, Iterable

from backend.exceptions import AnalyticsError, ValidationError
from backend.utils.math_utils import safe_division

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DATE_PATTERN_LEN: int = 10

#: Known detection bounding-box column names (CSV store convention).
_BBOX_KEYS: tuple[str, ...] = ("bbox_x", "bbox_y", "bbox_w", "bbox_h")


# ---------------------------------------------------------------------------
# Public data containers
# ---------------------------------------------------------------------------


class TransformResult:
    """Container for transformed analytical data.

    Attributes:
        detections: Transformed detection records.
        events: Transformed event records.
        alerts: Transformed alert records.
        kpis: Transformed KPI records.
        analytics: Transformed analytics records.
        videos: Transformed video records.
    """

    __slots__ = (
        "detections",
        "events",
        "alerts",
        "kpis",
        "analytics",
        "videos",
    )

    def __init__(
        self,
        *,
        detections: list[dict[str, Any]] | None = None,
        events: list[dict[str, Any]] | None = None,
        alerts: list[dict[str, Any]] | None = None,
        kpis: list[dict[str, Any]] | None = None,
        analytics: list[dict[str, Any]] | None = None,
        videos: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialise the transform result container."""
        self.detections = detections or []
        self.events = events or []
        self.alerts = alerts or []
        self.kpis = kpis or []
        self.analytics = analytics or []
        self.videos = videos or []

    def to_dict(self) -> dict[str, list[dict[str, Any]]]:
        """Return the transformed data keyed by store name."""
        return {
            "videos": self.videos,
            "detections": self.detections,
            "events": self.events,
            "alerts": self.alerts,
            "kpis": self.kpis,
            "analytics": self.analytics,
        }


# ---------------------------------------------------------------------------
# DataTransformer
# ---------------------------------------------------------------------------


class DataTransformer:
    """Transforms cleaned analytics records into analytical structures.

    Args:
        datetime_keys: Column names that hold ISO-8601 datetimes.  These
            are normalised to timezone-aware UTC strings.
    """

    def __init__(
        self,
        *,
        datetime_keys: tuple[str, ...] = (
            "created_at",
            "updated_at",
            "acknowledged_at",
            "processing_started_at",
            "processing_completed_at",
            "period_start",
            "period_end",
            "timestamp",
        ),
    ) -> None:
        """Initialise the data transformer."""
        self._datetime_keys = datetime_keys

    # ------------------------------------------------------------------
    # Detection transforms
    # ------------------------------------------------------------------

    def transform_detections(
        self,
        records: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Transform detection records into analytical detection rows.

        For each detection the following derived columns are added:

        * ``bbox_x`` / ``bbox_y`` / ``bbox_w`` / ``bbox_h`` — flattened
          bounding-box columns (already present in the CSV store
          convention, but preserved explicitly).
        * ``created_date`` — ``YYYY-MM-DD`` date string from
          ``created_at``.
        * ``confidence`` — normalised to a finite float in ``[0.0, 1.0]``
          (values outside the range are clamped, never invented).

        Args:
            records: Cleaned detection records.

        Returns:
            Transformed detection rows in input order.
        """
        transformed: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            row = dict(record)

            # Normalize bbox columns to finite floats (preserve existing).
            for key in _BBOX_KEYS:
                if key in row and row[key] is not None:
                    try:
                        row[key] = _to_finite_float(row[key], field=key)
                    except ValidationError:
                        logger.debug(
                            "Dropping invalid bbox column %s from detection.",
                            key,
                        )
                        row.pop(key, None)

            # Normalize confidence.
            if "confidence" in row and row["confidence"] is not None:
                try:
                    conf = _to_finite_float(row["confidence"], field="confidence")
                except ValidationError:
                    conf = None
                if conf is not None:
                    row["confidence"] = _clamp_confidence(conf)

            # Normalize known datetime columns to UTC ISO strings so the
            # analytical output is deterministic and JSON-serialisable
            # (consistent with the other record transforms).
            row = self._normalize_datetimes(row)

            # Date extraction.
            row["created_date"] = _extract_date(
                row.get("created_at"),
            )

            transformed.append(row)
        return transformed

    def detection_to_analytical(
        self,
        record: dict[str, Any],
    ) -> dict[str, Any]:
        """Convert a single detection into an analytical record.

        Args:
            record: A single detection record.

        Returns:
            Analytical record dictionary with derived columns.
        """
        if not isinstance(record, dict):
            raise AnalyticsError(
                "Detection record must be a dict, got "
                f"{type(record).__name__}."
            )
        row = dict(record)
        row["created_date"] = _extract_date(row.get("created_at"))
        return row

    # ------------------------------------------------------------------
    # Event transforms
    # ------------------------------------------------------------------

    def transform_events(
        self,
        records: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Transform event records.

        Args:
            records: Cleaned event records.

        Returns:
            Transformed event rows with normalised datetimes and a
            ``created_date`` column.
        """
        transformed: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            row = self._normalize_datetimes(dict(record))
            row["created_date"] = _extract_date(row.get("created_at"))
            transformed.append(row)
        return transformed

    # ------------------------------------------------------------------
    # Alert transforms
    # ------------------------------------------------------------------

    def transform_alerts(
        self,
        records: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Transform alert records.

        Args:
            records: Cleaned alert records.

        Returns:
            Transformed alert rows with normalised datetimes and a
            ``created_date`` column.
        """
        transformed: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            row = self._normalize_datetimes(dict(record))
            row["created_date"] = _extract_date(row.get("created_at"))
            transformed.append(row)
        return transformed

    # ------------------------------------------------------------------
    # KPI transforms
    # ------------------------------------------------------------------

    def transform_kpis(
        self,
        records: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Transform KPI records.

        Args:
            records: Cleaned KPI records.

        Returns:
            Transformed KPI rows with normalised timestamps.
        """
        transformed: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            row = self._normalize_datetimes(dict(record))
            if "value" in row and row["value"] is not None:
                try:
                    row["value"] = _to_finite_float(row["value"], field="value")
                except ValidationError:
                    logger.debug("Dropping non-finite KPI value.")
                    row.pop("value", None)
            transformed.append(row)
        return transformed

    # ------------------------------------------------------------------
    # Analytics-record transforms
    # ------------------------------------------------------------------

    def transform_analytics(
        self,
        records: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Transform aggregated-analytics records.

        Args:
            records: Cleaned analytics records.

        Returns:
            Transformed analytics rows.
        """
        transformed: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            row = self._normalize_datetimes(dict(record))
            if "value" in row and row["value"] is not None:
                try:
                    row["value"] = _to_finite_float(row["value"], field="value")
                except ValidationError:
                    logger.debug("Dropping non-finite analytics value.")
                    row.pop("value", None)
            transformed.append(row)
        return transformed

    # ------------------------------------------------------------------
    # Video transforms
    # ------------------------------------------------------------------

    def transform_videos(
        self,
        records: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Transform video metadata records.

        Args:
            records: Cleaned video records.

        Returns:
            Transformed video rows with normalised numeric and datetime
            columns plus ``duration_minutes`` and ``fps`` derived values
            where meaningful.
        """
        transformed: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            row = self._normalize_datetimes(dict(record))
            for key in ("duration_seconds", "fps", "total_frames", "file_size"):
                if key in row and row[key] is not None:
                    try:
                        row[key] = _to_finite_float(row[key], field=key)
                    except ValidationError:
                        logger.debug("Dropping invalid numeric %s.", key)
                        row.pop(key, None)

            duration = row.get("duration_seconds")
            if isinstance(duration, (int, float)):
                row["duration_minutes"] = safe_division(
                    float(duration), 60.0, default=0.0
                )
            transformed.append(row)
        return transformed

    # ------------------------------------------------------------------
    # Tracking statistics
    # ------------------------------------------------------------------

    def compute_tracking_stats(
        self,
        detections: Iterable[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute lightweight tracking statistics from detections.

        Args:
            detections: Cleaned/transformed detection records.

        Returns:
            Dictionary with keys:
            - ``unique_track_ids`` — number of distinct non-empty track
              IDs.
            - ``tracked_detections`` — count of detections carrying a
              track ID.
            - ``untracked_detections`` — count without a track ID.
            - ``per_track_counts`` — mapping of track ID → detection
              count (sorted by track ID).
        """
        track_counts: dict[str, int] = {}
        tracked = 0
        untracked = 0

        for det in detections:
            if not isinstance(det, dict):
                continue
            track_id = det.get("track_id")
            if track_id is not None and str(track_id).strip():
                track_id = str(track_id).strip()
                track_counts[track_id] = track_counts.get(track_id, 0) + 1
                tracked += 1
            else:
                untracked += 1

        return {
            "unique_track_ids": len(track_counts),
            "tracked_detections": tracked,
            "untracked_detections": untracked,
            "per_track_counts": dict(sorted(track_counts.items())),
        }

    # ------------------------------------------------------------------
    # Per-video transforms
    # ------------------------------------------------------------------

    def transform_per_video(
        self,
        detections: Iterable[dict[str, Any]],
        video_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return detections optionally scoped to a video.

        Args:
            detections: Detection records.
            video_id: Optional video ID to scope to.

        Returns:
            Detection rows matching the optional video scope.
        """
        if video_id is None:
            return list(detections)
        return [
            d for d in detections
            if isinstance(d, dict) and d.get("video_id") == video_id
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalize_datetimes(
        self,
        row: dict[str, Any],
    ) -> dict[str, Any]:
        """Normalise known datetime columns to UTC ISO strings."""
        for key in self._datetime_keys:
            if key in row and row[key] is not None:
                try:
                    row[key] = _normalize_datetime_str(row[key])
                except ValidationError:
                    logger.debug("Dropping invalid datetime %s.", key)
                    row.pop(key, None)
        return row


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _extract_date(value: Any) -> str | None:
    """Extract a ``YYYY-MM-DD`` date string from a timestamp value."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text[:_DATE_PATTERN_LEN] if text else None


def _normalize_datetime_str(value: Any) -> str:
    """Normalise a datetime-like value to a UTC ISO-8601 string."""
    parsed: datetime
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(
                f"Invalid ISO-8601 timestamp: {value!r}."
            ) from exc
    else:
        raise ValidationError(
            "Timestamp must be a datetime or string, got "
            f"{type(value).__name__}."
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _to_finite_float(value: Any, *, field: str) -> float:
    """Coerce a value to a finite Python float."""
    import math

    if isinstance(value, bool):
        raise ValidationError(f"field '{field}' must be a number, got bool.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"field '{field}' is not numeric: {value!r}."
        ) from exc
    if not math.isfinite(number):
        raise ValidationError(
            f"field '{field}' must be finite, got {value!r}."
        )
    return number


def _clamp_confidence(value: float) -> float:
    """Clamp a confidence value into ``[0.0, 1.0]``."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["DataTransformer", "TransformResult"]

