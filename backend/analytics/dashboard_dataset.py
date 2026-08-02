"""VisionOps AI — Dashboard Dataset Builder.

This module implements creation of dashboard-ready analytical data.  It
prepares the analytical dataset required by the existing dashboard
contract (``DashboardService`` and ``backend.schemas.dashboard``):

* overview summary counts,
* detection statistics (totals, classes, confidence bins, trends),
* alert summary,
* recent-video summaries,
* performance metrics,
* spoilage/freshness indicator values.

Design rules:

* This module does **not** implement FastAPI endpoints.
* It depends on :class:`~backend.analytics.aggregator.Aggregator` and
  :class:`~backend.analytics.transformer.DataTransformer` for reusable
  aggregation/transformation logic.
* Output is deterministic, serializable (scalar values, ISO datetimes),
  and safe on empty input.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Iterable

from backend.analytics.aggregator import Aggregator
from backend.analytics.transformer import DataTransformer
from backend.utils.date_utils import now_utc
from backend.utils.math_utils import safe_division

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_RECENT_ALERT_LIMIT: int = 20
_DEFAULT_TOP_CLASSES_LIMIT: int = 10
_DEFAULT_RECENT_VIDEO_LIMIT: int = 10

#: Video statuses that count as "processed" for performance metrics.
_PROCESSED_STATUSES: frozenset[str] = frozenset({"completed"})
_FAILED_STATUSES: frozenset[str] = frozenset({"failed"})


# ---------------------------------------------------------------------------
# DashboardDatasetBuilder
# ---------------------------------------------------------------------------


class DashboardDatasetBuilder:
    """Builds dashboard-ready analytical datasets.

    Args:
        aggregator: Optional injected :class:`Aggregator`.
        transformer: Optional injected :class:`DataTransformer`.
    """

    def __init__(
        self,
        aggregator: Aggregator | None = None,
        transformer: DataTransformer | None = None,
    ) -> None:
        """Initialise the dashboard dataset builder."""
        self._aggregator = aggregator or Aggregator()
        self._transformer = transformer or DataTransformer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        *,
        videos: Iterable[dict[str, Any]] | None = None,
        detections: Iterable[dict[str, Any]] | None = None,
        events: Iterable[dict[str, Any]] | None = None,
        alerts: Iterable[dict[str, Any]] | None = None,
        kpis: Iterable[dict[str, Any]] | None = None,
        period_days: int = 7,
    ) -> dict[str, Any]:
        """Build a complete dashboard-ready dataset.

        Args:
            videos: Video metadata records.
            detections: Detection records.
            events: Business-event records.
            alerts: Alert records.
            kpis: KPI records.
            period_days: Look-back period for performance metrics
                (default: 7).

        Returns:
            Dictionary with dashboard sections:
            - ``summary`` — overall counts and videos-by-status.
            - ``statistics`` — detection statistics.
            - ``alert_summary`` — alert totals and severity distribution.
            - ``recent_videos`` — recent video summaries.
            - ``performance_metrics`` — processing performance.
            - ``detection_trends`` — detections over time.
            - ``event_summary`` — event totals by type.
            - ``spoilage_risk_index`` — 0.0–1.0 indicator.
            - ``freshness_score`` — 0–100 indicator.
            - ``generated_at`` — UTC ISO timestamp.
        """
        videos = list(videos or [])
        detections = list(detections or [])
        events = list(events or [])
        alerts = list(alerts or [])
        kpis = list(kpis or [])

        # Transform detections so trends/tracking are available.
        transformed_detections = self._transformer.transform_detections(
            detections
        )

        summary = self._build_summary(
            videos=videos,
            detections=detections,
            events=events,
            alerts=alerts,
            kpis=kpis,
        )
        statistics = self._build_statistics(transformed_detections)
        alert_summary = self._build_alert_summary(alerts)
        recent_videos = self._build_recent_videos(
            videos=videos,
            detections=detections,
        )
        performance_metrics = self._build_performance_metrics(
            videos=videos,
            detections=detections,
            events=events,
            period_days=period_days,
        )
        detection_trends = self._aggregator.detections_over_time(
            transformed_detections
        )
        event_summary = self._aggregator.event_counts(events)

        # Freshness/risk indicators derived from existing data only.
        freshness = self._compute_freshness_score(transformed_detections)
        risk = self._compute_spoilage_risk_index(
            detections=transformed_detections,
            events=events,
        )

        dataset = {
            "summary": summary,
            "statistics": statistics,
            "alert_summary": alert_summary,
            "recent_videos": recent_videos,
            "performance_metrics": performance_metrics,
            "detection_trends": detection_trends,
            "event_summary": event_summary,
            "spoilage_risk_index": risk,
            "freshness_score": freshness,
            "generated_at": now_utc().isoformat(),
        }

        logger.info(
            "Dashboard dataset built: %d videos, %d detections, "
            "%d events, %d alerts.",
            len(videos),
            len(detections),
            len(events),
            len(alerts),
        )
        return dataset

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_summary(
        self,
        *,
        videos: list[dict[str, Any]],
        detections: list[dict[str, Any]],
        events: list[dict[str, Any]],
        alerts: list[dict[str, Any]],
        kpis: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build the dashboard summary section."""
        videos_by_status: dict[str, int] = {}
        for v in videos:
            if not isinstance(v, dict):
                continue
            status = str(v.get("status", "unknown")).strip() or "unknown"
            videos_by_status[status] = videos_by_status.get(status, 0) + 1

        return {
            "total_videos": sum(1 for v in videos if isinstance(v, dict)),
            "total_detections": self._aggregator.total_detections(detections),
            "total_events": self._aggregator.event_counts(events)["total"],
            "total_alerts": self._aggregator.alert_counts(alerts)["total"],
            "total_kpis": sum(1 for k in kpis if isinstance(k, dict)),
            "videos_by_status": dict(sorted(videos_by_status.items())),
        }

    def _build_statistics(
        self,
        detections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build the detection statistics section."""
        total = self._aggregator.total_detections(detections)
        class_counts = self._aggregator.detections_by_class(detections)
        conf = self._aggregator.confidence_statistics(detections)

        return {
            "total_detections": total,
            "unique_classes": len(class_counts),
            "average_confidence": conf["average_confidence"],
            "top_classes": self._aggregator.class_rankings(
                detections,
                limit=_DEFAULT_TOP_CLASSES_LIMIT,
            ),
            "confidence_distribution": self._aggregator.confidence_distribution(
                detections
            ),
            "detections_over_time": self._aggregator.detections_over_time(
                detections
            ),
        }

    def _build_alert_summary(
        self,
        alerts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build the alert summary section."""
        counts = self._aggregator.alert_counts(alerts)
        recent = self._recent_records(
            alerts,
            key="created_at",
            limit=_DEFAULT_RECENT_ALERT_LIMIT,
        )
        return {
            "total_alerts": counts["total"],
            "by_severity": counts["by_severity"],
            "acknowledged": counts["acknowledged"],
            "unacknowledged": counts["unacknowledged"],
            "recent_alerts": recent,
        }

    def _build_recent_videos(
        self,
        *,
        videos: list[dict[str, Any]],
        detections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build recent-video summary records.

        Each summary carries the video's total detection count derived
        from the supplied detections.
        """
        per_video = self._aggregator.detections_by_video(detections)
        recent = sorted(
            (v for v in videos if isinstance(v, dict)),
            key=lambda v: str(v.get("created_at", "")),
            reverse=True,
        )[:_DEFAULT_RECENT_VIDEO_LIMIT]

        summaries: list[dict[str, Any]] = []
        for v in recent:
            video_id = str(v.get("video_id", "")).strip()
            summaries.append(
                {
                    "video_id": video_id,
                    "filename": v.get("filename"),
                    "status": v.get("status"),
                    "duration_seconds": v.get("duration_seconds", 0.0),
                    "total_detections": per_video.get(video_id, 0),
                    "created_at": v.get("created_at"),
                    "thumbnail_path": v.get("thumbnail_path"),
                }
            )
        return summaries

    def _build_performance_metrics(
        self,
        *,
        videos: list[dict[str, Any]],
        detections: list[dict[str, Any]],
        events: list[dict[str, Any]],
        period_days: int,
    ) -> dict[str, Any]:
        """Build processing performance metrics.

        Processing times are derived from ``processing_started_at`` /
        ``processing_completed_at`` when available.  All rates use
        zero-safe division.
        """
        processed = sum(
            1 for v in videos
            if isinstance(v, dict)
            and str(v.get("status", "")).strip() in _PROCESSED_STATUSES
        )
        failed = sum(
            1 for v in videos
            if isinstance(v, dict)
            and str(v.get("status", "")).strip() in _FAILED_STATUSES
        )
        total_videos = sum(1 for v in videos if isinstance(v, dict))

        success_rate = round(
            safe_division(processed, total_videos, default=0.0), 4
        ) if total_videos else 0.0

        processing_times: list[float] = []
        for v in videos:
            if not isinstance(v, dict):
                continue
            start = v.get("processing_started_at")
            end = v.get("processing_completed_at")
            if not start or not end:
                continue
            try:
                start_dt = _to_utc_datetime(start)
                end_dt = _to_utc_datetime(end)
                delta = (end_dt - start_dt).total_seconds()
                if delta >= 0:
                    processing_times.append(delta)
            except (TypeError, ValueError):
                continue

        avg_time = (
            round(sum(processing_times) / len(processing_times), 4)
            if processing_times
            else 0.0
        )
        total_time = round(sum(processing_times), 4)
        longest = round(max(processing_times), 4) if processing_times else 0.0
        shortest = round(min(processing_times), 4) if processing_times else 0.0

        return {
            "period_days": period_days,
            "videos_processed": processed,
            "videos_failed": failed,
            "processing_success_rate": success_rate,
            "average_processing_time": avg_time,
            "total_processing_time": total_time,
            "longest_processing_time": longest,
            "shortest_processing_time": shortest,
            "total_detections_in_period": self._aggregator.total_detections(
                detections
            ),
            "total_events_in_period": self._aggregator.event_counts(events)[
                "total"
            ],
        }

    # ------------------------------------------------------------------
    # Indicator computations
    # ------------------------------------------------------------------

    def _compute_freshness_score(
        self,
        detections: list[dict[str, Any]],
    ) -> float:
        """Compute a freshness score (0–100) from detection data.

        Uses average confidence as a freshness proxy, consistent with
        the existing service-layer convention.

        Args:
            detections: Transformed detection records.

        Returns:
            Freshness score in ``[0.0, 100.0]`` (``100.0`` for empty
            input).
        """
        if not detections:
            return 100.0
        avg_conf = self._aggregator.confidence_statistics(detections)[
            "average_confidence"
        ]
        return round(avg_conf * 100.0, 2)

    def _compute_spoilage_risk_index(
        self,
        *,
        detections: list[dict[str, Any]],
        events: list[dict[str, Any]],
    ) -> float:
        """Compute a spoilage risk index (0.0–1.0).

        Uses high-risk class presence and dwell-type event counts as
        indicators, normalised to ``[0.0, 1.0]``.  This is a summary
        indicator derived from existing data, not a business decision.

        Args:
            detections: Transformed detection records.
            events: Event records.

        Returns:
            Risk index in ``[0.0, 1.0]`` (``0.0`` for empty input).
        """
        if not detections:
            return 0.0

        high_risk_classes = {"spoiled_food", "product", "pallet"}
        high_risk = sum(
            1 for d in detections
            if isinstance(d, dict)
            and str(d.get("class_name", "")).strip() in high_risk_classes
        )

        prolonged = sum(
            1 for e in events
            if isinstance(e, dict)
            and str(e.get("event_type", "")).strip().lower()
            in {"dwell", "idle", "stalled"}
        )

        total = len(detections)
        risk_ratio = safe_division(
            high_risk + prolonged * 2,
            total,
            default=0.0,
        )
        return round(min(max(risk_ratio, 0.0), 1.0), 4)

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _recent_records(
        records: list[dict[str, Any]],
        *,
        key: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return records sorted by a timestamp key (descending)."""
        filtered = [
            r for r in records
            if isinstance(r, dict) and r.get(key) is not None
        ]
        filtered.sort(key=lambda r: str(r.get(key, "")), reverse=True)
        return filtered[:limit]


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _to_utc_datetime(value: Any) -> datetime:
    """Normalise a datetime-like value to a timezone-aware UTC datetime."""
    parsed: datetime
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        raise TypeError(
            f"Cannot convert {type(value).__name__} to datetime."
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["DashboardDatasetBuilder"]

