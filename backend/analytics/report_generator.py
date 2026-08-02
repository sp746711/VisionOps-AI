"""VisionOps AI — Report Data Generation.

This module implements analytical report-data generation.  It produces
the derived summaries and metrics consumed by the report rendering layer
(``backend.services.report_service`` and the ``backend.reports``
package), **without** performing any PDF/Excel/CSV file rendering.

The responsibility boundary is intentionally strict:

* :class:`ReportDataGenerator` generates report **data** — metrics,
  grouped detection statistics, event summaries, alert summaries, KPI
  summaries and trend data.
* Actual file rendering (PDF/Excel/CSV/JSON output) belongs to the
  report service / reports package.

Design rules:

* Reuses the reusable aggregation/transformation logic from
  :class:`~backend.analytics.aggregator.Aggregator` and
  :class:`~backend.analytics.transformer.DataTransformer` — no
  business-rule duplication.
* Output is deterministic, serializable (scalar values, ISO datetimes)
  and safe on empty input.
* No hard-coded analytical values are ever produced; every metric is
  derived from the supplied records.

Usage::

    from backend.analytics import ReportDataGenerator

    generator = ReportDataGenerator()
    report_data = generator.generate(
        videos=videos, detections=detections,
        events=events, alerts=alerts, kpis=kpis,
    )
"""

from __future__ import annotations

import logging
from typing import Any, Iterable

from backend.analytics.aggregator import Aggregator
from backend.analytics.transformer import DataTransformer
from backend.utils.date_utils import now_utc

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_TOP_CLASSES_LIMIT: int = 10
_DEFAULT_TOP_EVENT_TYPES_LIMIT: int = 10


# ---------------------------------------------------------------------------
# ReportDataGenerator
# ---------------------------------------------------------------------------


class ReportDataGenerator:
    """Generates analytical report data and summaries.

    Args:
        aggregator: Optional injected :class:`Aggregator`.
        transformer: Optional injected :class:`DataTransformer`.
    """

    def __init__(
        self,
        aggregator: Aggregator | None = None,
        transformer: DataTransformer | None = None,
    ) -> None:
        """Initialise the report data generator."""
        self._aggregator = aggregator or Aggregator()
        self._transformer = transformer or DataTransformer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        *,
        videos: Iterable[dict[str, Any]] | None = None,
        detections: Iterable[dict[str, Any]] | None = None,
        events: Iterable[dict[str, Any]] | None = None,
        alerts: Iterable[dict[str, Any]] | None = None,
        kpis: Iterable[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generate a complete analytical report-data dictionary.

        Args:
            videos: Video metadata records.
            detections: Detection records.
            events: Business-event records.
            alerts: Alert records.
            kpis: KPI records.

        Returns:
            Dictionary with report-ready sections:

            - ``report_metrics`` — overall counts and derived rates.
            - ``detection_statistics`` — total, class/video breakdowns,
              confidence statistics and tracking summary.
            - ``event_summary`` — total events by type.
            - ``alert_summary`` — totals, severity distribution and
              acknowledgement state.
            - ``kpi_summary`` — KPI records grouped by metric.
            - ``class_distribution`` — ranked class list.
            - ``event_type_distribution`` — ranked event-type list.
            - ``detection_trends`` — detections over time.
            - ``generated_at`` — UTC ISO timestamp.
        """
        videos = list(videos or [])
        detections = list(detections or [])
        events = list(events or [])
        alerts = list(alerts or [])
        kpis = list(kpis or [])

        transformed_detections = self._transformer.transform_detections(
            detections
        )

        report_metrics = self._build_report_metrics(
            videos=videos,
            detections=transformed_detections,
            events=events,
            alerts=alerts,
            kpis=kpis,
        )
        detection_statistics = self._build_detection_statistics(
            transformed_detections
        )
        event_summary = self._aggregator.event_counts(events)
        alert_summary = self._aggregator.alert_counts(alerts)
        kpi_summary = self._aggregator.kpi_summary(kpis)

        class_distribution = self._aggregator.class_rankings(
            transformed_detections,
            limit=_DEFAULT_TOP_CLASSES_LIMIT,
        )
        event_type_distribution = self._ranked_types(
            events,
            key="event_type",
            limit=_DEFAULT_TOP_EVENT_TYPES_LIMIT,
        )
        detection_trends = self._aggregator.detections_over_time(
            transformed_detections
        )

        report_data: dict[str, Any] = {
            "report_metrics": report_metrics,
            "detection_statistics": detection_statistics,
            "event_summary": event_summary,
            "alert_summary": alert_summary,
            "kpi_summary": kpi_summary,
            "class_distribution": class_distribution,
            "event_type_distribution": event_type_distribution,
            "detection_trends": detection_trends,
            "generated_at": now_utc().isoformat(),
        }

        logger.info(
            "Report data generated: %d detections, %d events, "
            "%d alerts, %d KPIs.",
            detection_statistics["total_detections"],
            event_summary["total"],
            alert_summary["total"],
            len(kpis),
        )
        return report_data

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_report_metrics(
        self,
        *,
        videos: list[dict[str, Any]],
        detections: list[dict[str, Any]],
        events: list[dict[str, Any]],
        alerts: list[dict[str, Any]],
        kpis: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build the top-level report metrics section."""
        from backend.utils.math_utils import safe_division

        total_videos = sum(1 for v in videos if isinstance(v, dict))
        total_detections = self._aggregator.total_detections(detections)
        total_events = self._aggregator.event_counts(events)["total"]
        total_alerts = self._aggregator.alert_counts(alerts)["total"]
        total_kpis = sum(1 for k in kpis if isinstance(k, dict))

        # Derived rates (zero-safe).
        detections_per_event = round(
            safe_division(
                total_detections, total_events, default=0.0
            ),
            4,
        )
        detections_per_video = round(
            safe_division(
                total_detections, total_videos, default=0.0
            ),
            4,
        )
        events_per_video = round(
            safe_division(
                total_events, total_videos, default=0.0
            ),
            4,
        )
        alerts_per_video = round(
            safe_division(
                total_alerts, total_videos, default=0.0
            ),
            4,
        )

        return {
            "total_videos": total_videos,
            "total_detections": total_detections,
            "total_events": total_events,
            "total_alerts": total_alerts,
            "total_kpis": total_kpis,
            "detections_per_event": detections_per_event,
            "detections_per_video": detections_per_video,
            "events_per_video": events_per_video,
            "alerts_per_video": alerts_per_video,
        }

    def _build_detection_statistics(
        self,
        detections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build the detection statistics section."""
        by_class = self._aggregator.detections_by_class(detections)
        by_video = self._aggregator.detections_by_video(detections)
        confidence = self._aggregator.confidence_statistics(detections)
        tracking = self._transformer.compute_tracking_stats(detections)

        return {
            "total_detections": self._aggregator.total_detections(detections),
            "unique_classes": len(by_class),
            "detections_by_class": by_class,
            "detections_by_video": by_video,
            "average_confidence": confidence["average_confidence"],
            "min_confidence": confidence["min_confidence"],
            "max_confidence": confidence["max_confidence"],
            "confidence_distribution": self._aggregator.confidence_distribution(
                detections
            ),
            "tracking": tracking,
            "per_video_summaries": self._aggregator.per_video_summaries(
                detections
            ),
        }

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ranked_types(
        records: list[dict[str, Any]],
        *,
        key: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Rank records by a categorical column value (descending count)."""
        counts: dict[str, int] = {}
        for r in records:
            if not isinstance(r, dict):
                continue
            value = r.get(key)
            if value is None:
                continue
            label = str(value).strip() or "unknown"
            counts[label] = counts.get(label, 0) + 1

        ranked = sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:limit]
        return [
            {key: label, "count": count}
            for label, count in ranked
        ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["ReportDataGenerator"]

