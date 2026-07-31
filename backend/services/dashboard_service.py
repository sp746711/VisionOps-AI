"""VisionOps AI — Dashboard Service.

Provides business-logic orchestration for dashboard data aggregation,
summary statistics, and performance metrics. Aggregates data from
multiple CSV stores to serve the dashboard API endpoints.

Responsibilities:
    - Dashboard summary generation
    - Detection statistics
    - Alert summary
    - Performance metrics
    - Trend analysis

Usage::

    from backend.services import DashboardService

    service = DashboardService()
    summary = service.get_summary()
    det_stats = service.get_detection_stats()
    alerts = service.get_alert_summary()
    metrics = service.get_performance_metrics()
"""

from __future__ import annotations

import logging
from typing import Any

from backend.core.config import settings
from backend.exceptions import (
    ValidationError,
    StorageError,
)
from backend.storage import StorageService
from backend.utils.date_utils import now_utc
from backend.utils.math_utils import average, percentage, safe_division

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DashboardService
# ---------------------------------------------------------------------------


class DashboardService:
    """Orchestrates dashboard data aggregation and summary generation.

    This service provides pre-digested data for the dashboard API
    endpoints. It reads from CSV data stores and computes summary
    statistics, detection stats, alert summaries, and performance
    metrics — without implementing any low-level data manipulation.

    Dependency injection is used for the storage layer to improve
    testability.

    Raises:
        ValidationError: If input arguments are invalid.
        StorageError: If storage operations fail.
    """

    def __init__(
        self,
        storage: StorageService | None = None,
    ) -> None:
        """Initialise the dashboard service.

        Args:
            storage: Injected ``StorageService`` instance. When ``None``,
                a default instance is created.
        """
        self._storage = storage or StorageService()
        logger.info(
            "DashboardService initialised (storage=%s)",
            type(self._storage).__name__,
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(
        self,
    ) -> dict[str, Any]:
        """Get an overall dashboard summary with high-level counts.

        Returns:
            Dictionary with keys:
            - ``total_videos``: Number of video records.
            - ``total_detections``: Number of detection records.
            - ``total_events``: Number of business events.
            - ``total_alerts``: Number of alert records.
            - ``total_kpis``: Number of KPI records.
            - ``videos_by_status``: Video count grouped by status.
            - ``generated_at``: ISO-8601 timestamp.

        Raises:
            StorageError: If reading data stores fails.
        """
        try:
            videos = self._storage.read_csv_store("videos")
            detections = self._storage.read_csv_store("detections")
            events = self._storage.read_csv_store("events")
            alerts = self._storage.read_csv_store("alerts")
            kpis = self._storage.read_csv_store("kpis")
        except StorageError as exc:
            raise StorageError(
                f"Failed to read data for dashboard summary: {exc}"
            ) from exc

        # Videos by status
        videos_by_status: dict[str, int] = {}
        for v in videos:
            status = v.get("status", "unknown")
            videos_by_status[status] = videos_by_status.get(status, 0) + 1

        summary: dict[str, Any] = {
            "total_videos": len(videos),
            "total_detections": len(detections),
            "total_events": len(events),
            "total_alerts": len(alerts),
            "total_kpis": len(kpis),
            "videos_by_status": videos_by_status,
            "generated_at": now_utc().isoformat(),
        }

        logger.debug("Dashboard summary generated: %s", summary)
        return summary

    # ------------------------------------------------------------------
    # Detection Statistics
    # ------------------------------------------------------------------

    def get_detection_stats(
        self,
        video_id: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Get detection statistics.

        Args:
            video_id: Optional video ID to scope statistics.
            limit: Maximum number of class entries to return
                (default: 100).

        Returns:
            Dictionary with keys:
            - ``total_detections``: Total detection count.
            - ``unique_classes``: Number of distinct object classes.
            - ``average_confidence``: Mean confidence score.
            - ``top_classes``: Most frequent classes (limited to *limit*).
            - ``confidence_distribution``: Binned confidence counts.
            - ``detections_over_time``: Detection counts by date.

        Raises:
            ValidationError: If *limit* is invalid.
            StorageError: If reading the store fails.
        """
        if limit < 1 or limit > 1000:
            raise ValidationError(
                f"limit must be between 1 and 1000, got {limit}."
            )

        try:
            detections = self._storage.read_csv_store("detections")
        except StorageError as exc:
            raise StorageError(
                f"Failed to read detections for stats: {exc}"
            ) from exc

        if video_id:
            detections = [
                d for d in detections
                if d.get("video_id") == video_id
            ]

        total = len(detections)

        if not detections:
            return {
                "total_detections": 0,
                "unique_classes": 0,
                "average_confidence": 0.0,
                "top_classes": [],
                "confidence_distribution": {
                    "low": 0, "medium": 0, "high": 0,
                },
                "detections_over_time": [],
            }

        # Class counts
        class_counts: dict[str, int] = {}
        confidences: list[float] = []
        date_counts: dict[str, int] = {}

        for d in detections:
            cls = d.get("class_name", "unknown")
            class_counts[cls] = class_counts.get(cls, 0) + 1

            try:
                conf = float(d.get("confidence", 0.0))
                confidences.append(conf)
            except (ValueError, TypeError):
                pass

            created = d.get("created_at", "")[:10]
            if created:
                date_counts[created] = date_counts.get(created, 0) + 1

        # Top classes
        sorted_classes = sorted(
            class_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:limit]

        top_classes = [
            {"class_name": cls, "count": count}
            for cls, count in sorted_classes
        ]

        # Confidence distribution
        low = sum(1 for c in confidences if c < 0.3)
        medium = sum(1 for c in confidences if 0.3 <= c < 0.7)
        high = sum(1 for c in confidences if c >= 0.7)

        # Detections over time
        detections_over_time = [
            {"date": date, "count": count}
            for date, count in sorted(date_counts.items())
        ]

        stats: dict[str, Any] = {
            "total_detections": total,
            "unique_classes": len(class_counts),
            "average_confidence": round(
                average(confidences) if confidences else 0.0, 4
            ),
            "top_classes": top_classes,
            "confidence_distribution": {
                "low": low,
                "medium": medium,
                "high": high,
            },
            "detections_over_time": detections_over_time,
        }

        logger.debug(
            "Detection stats computed: %d total, %d classes",
            total,
            len(class_counts),
        )
        return stats

    # ------------------------------------------------------------------
    # Alert Summary
    # ------------------------------------------------------------------

    def get_alert_summary(
        self,
        min_severity: str = "low",
        limit: int = 50,
    ) -> dict[str, Any]:
        """Get a summary of alert data.

        Args:
            min_severity: Minimum severity to include — one of
                ``"low"``, ``"medium"``, ``"high"``, ``"critical"``
                (default: ``"low"``).
            limit: Maximum number of recent alerts to return
                (default: 50).

        Returns:
            Dictionary with keys:
            - ``total_alerts``: Total alert count.
            - ``by_severity``: Alert counts grouped by severity.
            - ``acknowledged``: Count of acknowledged alerts.
            - ``unacknowledged``: Count of unacknowledged alerts.
            - ``recent_alerts``: Most recent alerts (limited).
            - ``generated_at``: ISO-8601 timestamp.

        Raises:
            ValidationError: If *min_severity* or *limit* are invalid.
            StorageError: If reading the store fails.
        """
        VALID_SEVERITIES = {"low", "medium", "high", "critical"}
        SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

        if min_severity not in VALID_SEVERITIES:
            raise ValidationError(
                f"Invalid min_severity '{min_severity}'. "
                f"Valid: {', '.join(sorted(VALID_SEVERITIES))}."
            )
        if limit < 1 or limit > 500:
            raise ValidationError(
                f"limit must be between 1 and 500, got {limit}."
            )

        try:
            alerts = self._storage.read_csv_store("alerts")
        except StorageError as exc:
            raise StorageError(
                f"Failed to read alerts for summary: {exc}"
            ) from exc

        min_level = SEVERITY_ORDER.get(min_severity, 0)

        # Filter by severity
        filtered: list[dict[str, Any]] = []
        severity_counts: dict[str, int] = {}
        ack_count = 0
        unack_count = 0

        for alert in alerts:
            sev = alert.get("severity", "low").lower().strip()
            sev_level = SEVERITY_ORDER.get(sev, 0)

            if sev_level < min_level:
                continue

            filtered.append(alert)
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

            acknowledged = alert.get("acknowledged", "false").lower().strip()
            if acknowledged in ("true", "yes", "1"):
                ack_count += 1
            else:
                unack_count += 1

        # Recent alerts (sorted by created_at desc)
        sorted_alerts = sorted(
            filtered,
            key=lambda a: a.get("created_at", ""),
            reverse=True,
        )[:limit]

        summary: dict[str, Any] = {
            "total_alerts": len(filtered),
            "by_severity": severity_counts,
            "acknowledged": ack_count,
            "unacknowledged": unack_count,
            "recent_alerts": sorted_alerts,
            "generated_at": now_utc().isoformat(),
        }

        logger.debug(
            "Alert summary: %d total, %d ack, %d unack",
            len(filtered),
            ack_count,
            unack_count,
        )
        return summary

    # ------------------------------------------------------------------
    # Performance Metrics
    # ------------------------------------------------------------------

    def get_performance_metrics(
        self,
        days: int = 7,
    ) -> dict[str, Any]:
        """Get system performance metrics.

        Computes processing throughput, detection rates, and error
        rates over the specified time period.

        Args:
            days: Number of days to look back (default: 7).

        Returns:
            Dictionary with keys:
            - ``period_days``: The look-back period.
            - ``videos_processed``: Videos completed in period.
            - ``videos_failed``: Videos failed in period.
            - ``processing_success_rate``: Percentage success rate.
            - ``total_detections_in_period``: Detections in period.
            - ``average_detections_per_video``: Mean detections per video.
            - ``total_events_in_period``: Events in period.
            - ``generated_at``: ISO-8601 timestamp.

        Raises:
            ValidationError: If *days* is out of range.
            StorageError: If reading the store fails.
        """
        if days < 1 or days > 365:
            raise ValidationError(
                f"days must be between 1 and 365, got {days}."
            )

        try:
            videos = self._storage.read_csv_store("videos")
            detections = self._storage.read_csv_store("detections")
            events = self._storage.read_csv_store("events")
        except StorageError as exc:
            raise StorageError(
                f"Failed to read data for performance metrics: {exc}"
            ) from exc

        import datetime

        cutoff = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=days)
        )
        cutoff_str = cutoff.isoformat()[:19]

        # Filter videos by created_at
        videos_in_period = [
            v for v in videos
            if v.get("created_at", "")[:19] >= cutoff_str
        ]

        completed = sum(
            1 for v in videos_in_period
            if v.get("status") == "completed"
        )
        failed = sum(
            1 for v in videos_in_period
            if v.get("status") == "failed"
        )
        total_videos = len(videos_in_period)

        success_rate = round(
            safe_division(completed, total_videos, default=0.0) * 100.0,
            2,
        ) if total_videos > 0 else 100.0

        # Filter detections and events by time
        dets_in_period = [
            d for d in detections
            if d.get("created_at", "")[:19] >= cutoff_str
        ]
        evts_in_period = [
            e for e in events
            if e.get("created_at", "")[:19] >= cutoff_str
        ]

        avg_dets_per_vid = round(
            safe_division(
                len(dets_in_period),
                max(total_videos, 1),
                default=0.0,
            ),
            2,
        )

        metrics: dict[str, Any] = {
            "period_days": days,
            "videos_processed": completed,
            "videos_failed": failed,
            "processing_success_rate": success_rate,
            "total_detections_in_period": len(dets_in_period),
            "average_detections_per_video": avg_dets_per_vid,
            "total_events_in_period": len(evts_in_period),
            "generated_at": now_utc().isoformat(),
        }

        logger.debug(
            "Performance metrics computed: %d day(s), success=%.2f%%",
            days,
            success_rate,
        )
        return metrics

