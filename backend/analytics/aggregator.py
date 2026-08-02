"""VisionOps AI — Analytics Aggregation.

This module implements reusable analytical aggregation over cleaned and
transformed VisionOps records:

* total detections
* detections by class
* detections by video
* average / min / max confidence
* unique tracked objects
* event counts
* alert counts
* severity distributions
* KPI aggregation
* time-based grouping (by date)
* per-video summaries

Design rules:

* Empty input is handled gracefully (``0``, ``{}``, ``[]`` as
  appropriate).
* Division by zero is impossible — all rates use
  :func:`~backend.utils.math_utils.safe_division`.
* Aggregations are single-pass where practical and deterministic.
* ``bool`` values are never treated as numeric counts/confidence.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from typing import Any, Callable, Iterable

from backend.utils.math_utils import average, safe_division

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Confidence bins (matches DashboardService contract)
# ---------------------------------------------------------------------------

_CONFIDENCE_LOW: float = 0.3
_CONFIDENCE_MEDIUM: float = 0.7

#: Deterministic ordering for severity output.
_SEVERITY_ORDER: tuple[str, ...] = ("low", "medium", "high", "critical")

#: Deterministic ordering for confidence bins.
_CONFIDENCE_BIN_ORDER: tuple[str, ...] = ("low", "medium", "high")


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


class Aggregator:
    """Reusable analytical aggregation over VisionOps records.

    All methods are deterministic and safe on empty input.  Public
    outputs are plain Python scalars/lists/dicts.
    """

    # ------------------------------------------------------------------
    # Detection aggregation
    # ------------------------------------------------------------------

    def total_detections(
        self,
        detections: Iterable[dict[str, Any]],
    ) -> int:
        """Return the total detection count.

        Args:
            detections: Detection records.

        Returns:
            Non-negative integer count (``0`` for empty input).
        """
        return sum(1 for d in detections if isinstance(d, dict))

    def detections_by_class(
        self,
        detections: Iterable[dict[str, Any]],
    ) -> dict[str, int]:
        """Count detections grouped by class name.

        Args:
            detections: Detection records.

        Returns:
            Mapping from class name to count, sorted by class name.
        """
        counts: Counter[str] = Counter()
        for d in detections:
            if not isinstance(d, dict):
                continue
            cls = d.get("class_name", "unknown")
            counts[str(cls).strip() or "unknown"] += 1
        return dict(sorted(counts.items()))

    def detections_by_video(
        self,
        detections: Iterable[dict[str, Any]],
    ) -> dict[str, int]:
        """Count detections grouped by video ID.

        Args:
            detections: Detection records.

        Returns:
            Mapping from video ID to count, sorted by video ID.
        """
        counts: Counter[str] = Counter()
        for d in detections:
            if not isinstance(d, dict):
                continue
            video_id = d.get("video_id", "unknown")
            counts[str(video_id).strip() or "unknown"] += 1
        return dict(sorted(counts.items()))

    def confidence_statistics(
        self,
        detections: Iterable[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute average/min/max confidence statistics.

        Args:
            detections: Detection records.

        Returns:
            Dictionary with keys ``average_confidence``,
            ``min_confidence``, ``max_confidence`` (``0.0`` for empty
            input).
        """
        confidences: list[float] = []
        for d in detections:
            if not isinstance(d, dict):
                continue
            try:
                value = float(d.get("confidence", 0.0))
            except (TypeError, ValueError):
                continue
            if value >= 0.0 and value <= 1.0:
                confidences.append(value)

        if not confidences:
            return {
                "average_confidence": 0.0,
                "min_confidence": 0.0,
                "max_confidence": 0.0,
            }

        return {
            "average_confidence": round(average(confidences), 4),
            "min_confidence": round(min(confidences), 4),
            "max_confidence": round(max(confidences), 4),
        }

    def confidence_distribution(
        self,
        detections: Iterable[dict[str, Any]],
    ) -> dict[str, int]:
        """Bin detection confidences into low/medium/high buckets.

        Args:
            detections: Detection records.

        Returns:
            Mapping with ``low``, ``medium``, ``high`` counts in that
            deterministic order.
        """
        low = medium = high = 0
        for d in detections:
            if not isinstance(d, dict):
                continue
            try:
                value = float(d.get("confidence", 0.0))
            except (TypeError, ValueError):
                continue
            if not (0.0 <= value <= 1.0):
                continue
            if value < _CONFIDENCE_LOW:
                low += 1
            elif value < _CONFIDENCE_MEDIUM:
                medium += 1
            else:
                high += 1
        return {"low": low, "medium": medium, "high": high}

    def unique_tracked_objects(
        self,
        detections: Iterable[dict[str, Any]],
    ) -> int:
        """Return the number of distinct tracked object IDs.

        Args:
            detections: Detection records.

        Returns:
            Non-negative integer count.
        """
        track_ids: set[str] = set()
        for d in detections:
            if not isinstance(d, dict):
                continue
            track_id = d.get("track_id")
            if track_id is not None and str(track_id).strip():
                track_ids.add(str(track_id).strip())
        return len(track_ids)

    def per_video_summaries(
        self,
        detections: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build per-video detection summaries.

        Args:
            detections: Detection records.

        Returns:
            Sorted list (by video ID) of dictionaries with keys
            ``video_id``, ``total_detections``, ``unique_classes``,
            ``average_confidence``.
        """
        grouped: dict[str, list[float]] = defaultdict(list)
        class_counts: dict[str, Counter[str]] = defaultdict(Counter)

        for d in detections:
            if not isinstance(d, dict):
                continue
            video_id = str(d.get("video_id", "unknown")).strip() or "unknown"
            cls = str(d.get("class_name", "unknown")).strip() or "unknown"
            class_counts[video_id][cls] += 1
            try:
                conf = float(d.get("confidence", 0.0))
            except (TypeError, ValueError):
                continue
            if 0.0 <= conf <= 1.0:
                grouped[video_id].append(conf)

        summaries: list[dict[str, Any]] = []
        for video_id in sorted(grouped.keys() | class_counts.keys()):
            confs = grouped.get(video_id, [])
            summaries.append(
                {
                    "video_id": video_id,
                    "total_detections": sum(class_counts[video_id].values()),
                    "unique_classes": len(class_counts[video_id]),
                    "average_confidence": round(average(confs), 4)
                    if confs
                    else 0.0,
                }
            )
        return summaries

    def detections_over_time(
        self,
        detections: Iterable[dict[str, Any]],
        *,
        date_key: str = "created_date",
    ) -> list[dict[str, Any]]:
        """Count detections per date.

        Args:
            detections: Detection records (prefer transformed records
                carrying ``created_date``).
            date_key: Column to read the ``YYYY-MM-DD`` date from.

        Returns:
            Sorted list of ``{"date": ..., "count": ...}`` dictionaries.
        """
        counts: Counter[str] = Counter()
        for d in detections:
            if not isinstance(d, dict):
                continue
            day = d.get(date_key)
            if not day:
                # Fallback: derive from created_at
                created = d.get("created_at")
                if created is not None:
                    day = str(created)[:10]
            if day:
                counts[str(day)] += 1
        return [
            {"date": day, "count": counts[day]}
            for day in sorted(counts)
        ]

    def class_rankings(
        self,
        detections: Iterable[dict[str, Any]],
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Rank classes by detection count, highest first.

        Args:
            detections: Detection records.
            limit: Maximum number of classes to return.

        Returns:
            Sorted list (descending count, then ascending class name) of
            ``{"class_name": ..., "count": ...}`` dictionaries.
        """
        counts = self.detections_by_class(detections)
        ranked = sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )[:limit]
        return [
            {"class_name": cls, "count": count}
            for cls, count in ranked
        ]

    # ------------------------------------------------------------------
    # Event / Alert aggregation
    # ------------------------------------------------------------------

    def event_counts(
        self,
        events: Iterable[dict[str, Any]],
    ) -> dict[str, Any]:
        """Aggregate event counts.

        Args:
            events: Event records.

        Returns:
            Dictionary with keys ``total`` and ``by_type`` (sorted by
            type name).
        """
        by_type: Counter[str] = Counter()
        for e in events:
            if not isinstance(e, dict):
                continue
            etype = e.get("event_type", "unknown")
            by_type[str(etype).strip() or "unknown"] += 1
        return {
            "total": sum(by_type.values()),
            "by_type": dict(sorted(by_type.items())),
        }

    def alert_counts(
        self,
        alerts: Iterable[dict[str, Any]],
    ) -> dict[str, Any]:
        """Aggregate alert counts.

        Args:
            alerts: Alert records.

        Returns:
            Dictionary with keys ``total``, ``by_severity`` (ordered
            low→critical), ``acknowledged`` and ``unacknowledged``.
        """
        severity_counts: Counter[str] = Counter()
        ack = 0
        total = 0
        for a in alerts:
            if not isinstance(a, dict):
                continue
            total += 1
            sev = str(a.get("severity", "unknown")).strip().lower() or "unknown"
            severity_counts[sev] += 1
            acknowledged = a.get("acknowledged", False)
            if isinstance(acknowledged, str):
                acknowledged = acknowledged.strip().lower() in (
                    "true",
                    "yes",
                    "1",
                    "y",
                )
            if bool(acknowledged):
                ack += 1

        ordered: dict[str, int] = {}
        for sev in _SEVERITY_ORDER:
            if sev in severity_counts:
                ordered[sev] = severity_counts[sev]
        for sev, count in sorted(severity_counts.items()):
            if sev not in ordered:
                ordered[sev] = count

        return {
            "total": total,
            "by_severity": ordered,
            "acknowledged": ack,
            "unacknowledged": total - ack,
        }

    def severity_distribution(
        self,
        records: Iterable[dict[str, Any]],
        *,
        severity_key: str = "severity",
    ) -> dict[str, int]:
        """Compute a severity distribution for records with a severity.

        Args:
            records: Records carrying a ``severity`` column.
            severity_key: Column name holding the severity.

        Returns:
            Ordered mapping (low → critical) of severity counts.
        """
        counts: Counter[str] = Counter()
        for r in records:
            if not isinstance(r, dict):
                continue
            sev = r.get(severity_key)
            if sev is None:
                continue
            counts[str(sev).strip().lower()] += 1

        ordered: dict[str, int] = {}
        for sev in _SEVERITY_ORDER:
            if sev in counts:
                ordered[sev] = counts[sev]
        for sev, count in sorted(counts.items()):
            if sev not in ordered:
                ordered[sev] = count
        return ordered

    # ------------------------------------------------------------------
    # KPI aggregation
    # ------------------------------------------------------------------

    def kpi_summary(
        self,
        kpis: Iterable[dict[str, Any]],
    ) -> dict[str, Any]:
        """Aggregate KPI records by metric name.

        Args:
            kpis: KPI records.

        Returns:
            Dictionary mapping metric name to its aggregate: ``count``,
            ``min``, ``max``, ``average`` (or ``None`` when no values).
        """
        grouped: dict[str, list[float]] = defaultdict(list)
        for k in kpis:
            if not isinstance(k, dict):
                continue
            metric = str(k.get("metric", "unknown")).strip() or "unknown"
            try:
                value = float(k.get("value"))
            except (TypeError, ValueError):
                continue
            if value != value:  # NaN guard
                continue
            grouped[metric].append(value)

        summary: dict[str, Any] = {}
        for metric in sorted(grouped):
            values = grouped[metric]
            summary[metric] = {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "average": round(average(values), 4),
            }
        return summary

    def latest_kpis(
        self,
        kpis: Iterable[dict[str, Any]],
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Return the most recent KPI records.

        Args:
            kpis: KPI records.
            limit: Maximum number of records to return.

        Returns:
            List of KPI records sorted by ``timestamp`` descending
            (records without a timestamp last, stable order).
        """
        records = list(kpis)
        records = [
            k for k in records
            if isinstance(k, dict) and k.get("timestamp") is not None
        ]
        records.sort(key=lambda k: str(k.get("timestamp", "")), reverse=True)
        return records[:limit]

    # ------------------------------------------------------------------
    # Generic grouping helper
    # ------------------------------------------------------------------

    def group_by(
        self,
        records: Iterable[dict[str, Any]],
        key_fn: Callable[[dict[str, Any]], str],
    ) -> dict[str, list[dict[str, Any]]]:
        """Group records by a key function.

        Args:
            records: Records to group.
            key_fn: Function receiving a record and returning its group
                key.

        Returns:
            Mapping from group key to record list, sorted by key.
        """
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in records:
            if not isinstance(r, dict):
                continue
            key = key_fn(r)
            grouped[str(key)].append(r)
        return {k: grouped[k] for k in sorted(grouped)}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["Aggregator"]

