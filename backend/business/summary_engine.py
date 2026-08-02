"""VisionOps AI — Summary Engine.

Combines business outputs into concise operational summaries.

Possible inputs:
    * events
    * alerts
    * KPIs
    * detections
    * business-engine output

Possible outputs:
    * counts
    * severity summary
    * KPI summary
    * operational status

The SummaryEngine produces **domain/business summaries** only.  Deeper
analytical transformation/aggregation belongs to
``backend.analytics``; this engine does not duplicate it.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.utils.date_utils import now_utc

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["SummaryEngine"]


class SummaryEngine:
    """Domain summary engine — produces concise business summaries.

    The engine is storage-agnostic and receives an optional storage
    service for reading detection/event/alert/KPI data.  It returns a
    plain dictionary summary.

    Args:
        storage: Optional storage service (injected for testability).
    """

    def __init__(self, storage: Any | None = None) -> None:
        """Initialise the summary engine.

        Args:
            storage: Optional storage service for reading data.
        """
        self._storage = storage

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_summary(
        self,
        video_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate a concise operational summary for a video.

        Args:
            video_id: Video ID to scope the summary.  When ``None`` or
                empty, the summary covers all stored data.

        Returns:
            A dictionary with:
            * ``video_id`` — the scoped video (or ``"global"``).
            * ``total_detections`` — detection count.
            * ``total_events`` — event count.
            * ``total_alerts`` — alert count.
            * ``total_kpis`` — KPI count.
            * ``severity_summary`` — per-severity event counts.
            * ``class_summary`` — per-class detection counts.
            * ``generated_at`` — UTC ISO timestamp.

        Raises:
            ValidationError: If *video_id* is provided but empty.
        """
        if video_id is not None and not video_id.strip():
            raise ValueError("video_id must not be empty.")

        detections = self._read_store("detections")
        events = self._read_store("events")
        alerts = self._read_store("alerts")
        kpis = self._read_store("kpis")

        if video_id:
            detections = [r for r in detections if r.get("video_id") == video_id]
            events = [r for r in events if r.get("video_id") == video_id]
            alerts = [r for r in alerts if r.get("video_id") == video_id]
            kpis = [r for r in kpis if r.get("video_id") == video_id]

        # Class summary
        class_counts: dict[str, int] = {}
        for det in detections:
            cls = str(det.get("class_name", "unknown"))
            class_counts[cls] = class_counts.get(cls, 0) + 1

        # Severity summary from events
        severity_counts: dict[str, int] = {}
        for evt in events:
            sev = str(evt.get("severity", "unknown"))
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        summary: dict[str, Any] = {
            "video_id": video_id or "global",
            "total_detections": len(detections),
            "total_events": len(events),
            "total_alerts": len(alerts),
            "total_kpis": len(kpis),
            "severity_summary": severity_counts,
            "class_summary": class_counts,
            "generated_at": now_utc().isoformat(),
        }

        logger.debug(
            "SummaryEngine.generate_summary: video_id=%s, detections=%d, "
            "events=%d, alerts=%d",
            video_id or "global",
            len(detections),
            len(events),
            len(alerts),
        )
        return summary

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_store(self, name: str) -> list[dict[str, Any]]:
        """Read a CSV store defensively.

        Args:
            name: Store name (e.g. ``"detections"``).

        Returns:
            A list of row dictionaries.  Returns ``[]`` when the store
            is unavailable or the storage service is not injected.
        """
        if self._storage is None:
            return []
        try:
            records = self._storage.read_csv_store(name)
        except Exception:
            logger.warning(
                "SummaryEngine: failed to read store '%s'.", name, exc_info=True
            )
            return []
        return _safe_list(records)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _safe_list(value: Any) -> list[dict[str, Any]]:
    """Convert a value into a list of dictionaries.

    Handles mocked storage services that may return non-list values.

    Args:
        value: Raw value from a storage read.

    Returns:
        A list of dictionaries (``[]`` when the value is not usable).
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [r for r in value if isinstance(r, dict)]
    if isinstance(value, tuple):
        return [r for r in value if isinstance(r, dict)]
    try:
        return [r for r in value if isinstance(r, dict)]
    except TypeError:
        return []


