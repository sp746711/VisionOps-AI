"""VisionOps AI — KPI Engine.

Coordinates the calculators and creates standardized
:class:`~backend.models.kpi.KPI` results.

Every KPI:

* derives from real detection/event data (never fabricated),
* has an explicit formula and a meaningful unit,
* handles empty data gracefully,
* avoids division-by-zero,
* produces a finite numeric value.

The engine reuses the ``kpi_id``/``metric``/``value``/``unit``/
``video_id``/``timestamp`` dictionary format already used by the
analytics service, so downstream consumers (dashboard, reports) can
consume KPI records uniformly.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.utils.date_utils import now_utc
from backend.utils.id_generator import generate_uuid4

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["KPIEngine"]

#: Metrics computed by the KPI engine with their units.
_DETECTION_RATE_METRIC: str = "detection_rate"
_AVERAGE_CONFIDENCE_METRIC: str = "average_confidence"
_TOTAL_DETECTIONS_METRIC: str = "total_detections"
_TOTAL_EVENTS_METRIC: str = "total_events"


class KPIEngine:
    """Domain KPI engine — computes operational KPIs from real data.

    The engine is storage-agnostic and receives an optional storage
    service for reading detection/event data.  It returns KPI records as
    plain dictionaries compatible with the
    :class:`~backend.models.kpi.KPI` model.

    Args:
        storage: Optional storage service (injected for testability).
    """

    def __init__(self, storage: Any | None = None) -> None:
        """Initialise the KPI engine.

        Args:
            storage: Optional storage service for reading data.
        """
        self._storage = storage

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_detection_rate(
        self,
        video_id: str | None = None,
    ) -> dict[str, Any]:
        """Calculate the detection rate KPI.

        Formula:
            ``detection_rate = total_detections / total_events``

        The result is ``0.0`` when there are no events or no detections
        (division-by-zero protected).  The metric name is
        ``"detection_rate"`` and the unit is ``"ratio"``.

        Args:
            video_id: Optional video ID to scope the calculation.

        Returns:
            A KPI dictionary with keys ``kpi_id``, ``video_id``,
            ``metric``, ``value``, ``unit``, ``timestamp``.

        Raises:
            ValidationError: If *video_id* is provided but empty.
        """
        if video_id is not None and not video_id.strip():
            raise ValueError("video_id must not be empty.")

        detections = self._load_detections(video_id)
        events = self._load_events(video_id)

        total_detections = len(detections)
        total_events = len(events)

        value = 0.0
        if total_events > 0 and total_detections > 0:
            value = round(total_detections / total_events, 4)

        return self._make_kpi(
            metric=_DETECTION_RATE_METRIC,
            value=value,
            unit="ratio",
            video_id=video_id or "global",
        )

    def calculate_confidence_score(
        self,
        video_id: str | None = None,
    ) -> dict[str, Any]:
        """Calculate the average confidence KPI.

        Formula:
            ``average_confidence = sum(confidence) / count(detections)``

        The result is ``0.0`` when there are no detections.  The metric
        name is ``"average_confidence"`` and the unit is ``"score"``.

        Args:
            video_id: Optional video ID to scope the calculation.

        Returns:
            A KPI dictionary (see :meth:`calculate_detection_rate`).

        Raises:
            ValidationError: If *video_id* is provided but empty.
        """
        if video_id is not None and not video_id.strip():
            raise ValueError("video_id must not be empty.")

        detections = self._load_detections(video_id)

        total = 0.0
        count = 0
        for det in detections:
            if not isinstance(det, dict):
                continue
            raw = det.get("confidence")
            try:
                confidence = float(raw)
            except (TypeError, ValueError):
                continue
            if not _is_finite(confidence) or confidence < 0.0:
                continue
            total += confidence
            count += 1

        value = round(total / count, 4) if count > 0 else 0.0

        return self._make_kpi(
            metric=_AVERAGE_CONFIDENCE_METRIC,
            value=value,
            unit="score",
            video_id=video_id or "global",
        )

    def calculate_total_detections(
        self,
        video_id: str | None = None,
    ) -> dict[str, Any]:
        """Calculate the total-detection-count KPI.

        Formula:
            ``total_detections = count(detections)``

        Args:
            video_id: Optional video ID to scope the calculation.

        Returns:
            A KPI dictionary with metric ``"total_detections"`` and
            unit ``"count"``.
        """
        if video_id is not None and not video_id.strip():
            raise ValueError("video_id must not be empty.")
        detections = self._load_detections(video_id)
        return self._make_kpi(
            metric=_TOTAL_DETECTIONS_METRIC,
            value=len(detections),
            unit="count",
            video_id=video_id or "global",
        )

    def calculate_total_events(
        self,
        video_id: str | None = None,
    ) -> dict[str, Any]:
        """Calculate the total-event-count KPI.

        Formula:
            ``total_events = count(events)``

        Args:
            video_id: Optional video ID to scope the calculation.

        Returns:
            A KPI dictionary with metric ``"total_events"`` and unit
            ``"count"``.
        """
        if video_id is not None and not video_id.strip():
            raise ValueError("video_id must not be empty.")
        events = self._load_events(video_id)
        return self._make_kpi(
            metric=_TOTAL_EVENTS_METRIC,
            value=len(events),
            unit="count",
            video_id=video_id or "global",
        )

    def calculate_all(
        self,
        video_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Calculate all primary KPI records for a video.

        Args:
            video_id: Optional video ID to scope the calculation.

        Returns:
            A list of KPI dictionaries (never ``None``).
        """
        return [
            self.calculate_detection_rate(video_id=video_id),
            self.calculate_confidence_score(video_id=video_id),
            self.calculate_total_detections(video_id=video_id),
            self.calculate_total_events(video_id=video_id),
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_detections(self, video_id: str | None) -> list[dict[str, Any]]:
        """Load detection records scoped to a video.

        Args:
            video_id: Optional video ID filter.

        Returns:
            List of detection dictionaries (never ``None``).
        """
        records = self._read_store("detections")
        if video_id:
            records = [
                r for r in records if r.get("video_id") == video_id
            ]
        return records

    def _load_events(self, video_id: str | None) -> list[dict[str, Any]]:
        """Load event records scoped to a video.

        Args:
            video_id: Optional video ID filter.

        Returns:
            List of event dictionaries (never ``None``).
        """
        records = self._read_store("events")
        if video_id:
            records = [
                r for r in records if r.get("video_id") == video_id
            ]
        return records

    def _read_store(self, name: str) -> list[dict[str, Any]]:
        """Read a CSV store defensively.

        Args:
            name: Store name (``"detections"`` or ``"events"``).

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
                "KPIEngine: failed to read store '%s'.", name, exc_info=True
            )
            return []
        return _safe_list(records)

    @staticmethod
    def _make_kpi(
        metric: str,
        value: float | int,
        unit: str,
        video_id: str,
    ) -> dict[str, Any]:
        """Build a standardised KPI dictionary.

        Args:
            metric: KPI metric name.
            value: Numeric KPI value.
            unit: KPI unit label.
            video_id: Video ID (or ``"global"``).

        Returns:
            KPI dictionary compatible with
            :class:`~backend.models.kpi.KPI`.
        """
        return {
            "kpi_id": f"kpi_{metric}_{video_id}_{generate_uuid4()}",
            "video_id": video_id,
            "metric": metric,
            "value": value,
            "unit": unit,
            "timestamp": now_utc().isoformat(),
        }


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


def _is_finite(value: float) -> bool:
    """Return ``True`` for a finite, non-bool float."""
    import math

    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


