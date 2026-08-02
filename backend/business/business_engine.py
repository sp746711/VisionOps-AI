"""VisionOps AI — Business Engine.

High-level facade/orchestrator for the business layer.

Conceptual flow:
    Validated detections/tracks
        ↓
    Rules
        ↓
    EventEngine
        ↓
    Events
        ↓
    AlertEngine
        ↓
    Alerts
        ↓
    KPIEngine
        ↓
    KPIs
        ↓
    SummaryEngine
        ↓
    Business Result

The BusinessEngine exposes convenience methods for services/workers to
call the business layer without knowing every individual
rule/calculator.  Components are injected (dependency injection) so the
engine is testable without storage, AI models, or external services.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.business.alert_engine import AlertEngine
from backend.business.event_engine import EventEngine
from backend.business.kpi_engine import KPIEngine
from backend.business.summary_engine import SummaryEngine
from backend.exceptions import ValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["BusinessEngine"]


class BusinessEngine:
    """High-level business facade.

    Orchestrates the event, alert, KPI and summary engines.  Each engine
    may be injected; when not supplied, a default engine is created
    against the same storage service.

    Args:
        storage: Optional storage service passed to all sub-engines.
        event_engine: Optional :class:`EventEngine` instance.
        alert_engine: Optional :class:`AlertEngine` instance.
        kpi_engine: Optional :class:`KPIEngine` instance.
        summary_engine: Optional :class:`SummaryEngine` instance.
    """

    def __init__(
        self,
        storage: Any | None = None,
        event_engine: EventEngine | None = None,
        alert_engine: AlertEngine | None = None,
        kpi_engine: KPIEngine | None = None,
        summary_engine: SummaryEngine | None = None,
    ) -> None:
        """Initialise the business engine with optional sub-engines.

        Args:
            storage: Optional storage service.
            event_engine: Optional event engine.
            alert_engine: Optional alert engine.
            kpi_engine: Optional KPI engine.
            summary_engine: Optional summary engine.
        """
        self._storage = storage
        self.event_engine = event_engine or EventEngine(storage=storage)
        self.alert_engine = alert_engine or AlertEngine(storage=storage)
        self.kpi_engine = kpi_engine or KPIEngine(storage=storage)
        self.summary_engine = summary_engine or SummaryEngine(storage=storage)

    # ------------------------------------------------------------------
    # Convenience orchestration
    # ------------------------------------------------------------------

    def analyze(
        self,
        video_id: str | None = None,
    ) -> dict[str, Any]:
        """Run the full business pipeline for a video.

        Executes event processing, alert generation, KPI calculation and
        summary generation, returning a combined business result.

        Args:
            video_id: Video ID to analyze.

        Returns:
            A dictionary with ``events``, ``alerts``, ``kpis`` and
            ``summary`` keys.

        Raises:
            ValidationError: If *video_id* is empty.
        """
        if video_id is not None and not video_id.strip():
            raise ValidationError(
                "BusinessEngine.analyze: video_id must not be empty."
            )

        events = self.event_engine.process_events(video_id=video_id)
        alerts = self.alert_engine.generate_alerts(video_id=video_id)
        kpis = self.kpi_engine.calculate_all(video_id=video_id)
        summary = self.summary_engine.generate_summary(video_id=video_id)

        return {
            "video_id": video_id or "global",
            "events": events,
            "alerts": alerts,
            "kpis": kpis,
            "summary": summary,
        }

    # ------------------------------------------------------------------
    # Spoilage scoring (legacy contract)
    # ------------------------------------------------------------------

    def compute_spoilage_score(
        self,
        video_id: str | None = None,
    ) -> dict[str, Any]:
        """Compute a spoilage-risk score for a video.

        The score is derived from real detection/event data only.  With
        no data, a safe ``0.0`` / ``"low"`` / ``[]`` result is returned
        — no fake risk is fabricated.

        Args:
            video_id: Video ID to scope the score.

        Returns:
            A dictionary with ``spoilage_score``, ``risk_level`` and
            ``factors`` keys.

        Raises:
            ValidationError: If *video_id* is empty.
        """
        if video_id is not None and not video_id.strip():
            raise ValidationError(
                "BusinessEngine.compute_spoilage_score: video_id must "
                "not be empty."
            )

        detections = self._read_store("detections")
        events = self._read_store("events")

        if video_id:
            detections = [
                r
                for r in detections
                if r.get("video_id") in (None, "", video_id)
            ]
            events = [
                r
                for r in events
                if r.get("video_id") in (None, "", video_id)
            ]

        # Risk indicators from real data
        high_risk_classes = {"product", "pallet", "spoiled_food"}
        high_risk_count = sum(
            1
            for d in detections
            if str(d.get("class_name", "")).strip().lower() in high_risk_classes
        )

        # Prolonged dwell/idle/stalled events
        prolonged_events = sum(
            1
            for e in events
            if str(e.get("event_type", "")).strip().lower()
            in {"dwell", "idle", "stalled", "spoilage_risk"}
        )

        total_items = len(detections) or 1
        risk_ratio = (high_risk_count + prolonged_events * 2) / total_items
        score = round(max(0.0, min(risk_ratio * 100.0, 100.0)), 2)

        factors: list[str] = []
        if high_risk_count > 10:
            factors.append(f"High count of risk objects ({high_risk_count})")
        if prolonged_events > 5:
            factors.append(
                f"Prolonged dwell/idle events detected ({prolonged_events})"
            )
        if score > 70:
            factors.append("Elevated spoilage risk index")

        risk_level = (
            "high"
            if score >= 70
            else "medium"
            if score >= 40
            else "low"
        )

        return {
            "spoilage_score": score,
            "risk_level": risk_level,
            "factors": factors,
        }

    # ------------------------------------------------------------------
    # Cold chain validation (legacy contract)
    # ------------------------------------------------------------------

    def validate_cold_chain(
        self,
        video_id: str | None = None,
    ) -> dict[str, Any]:
        """Validate the cold chain for a video.

        Detects ``temperature_breach`` events (and similar cold-chain
        breach indicators) in the event stream.

        Args:
            video_id: Video ID to scope the validation.

        Returns:
            A dictionary with ``is_valid``, ``breaches`` and
            ``severity`` keys.

        Raises:
            ValidationError: If *video_id* is empty.
        """
        if video_id is not None and not video_id.strip():
            raise ValidationError(
                "BusinessEngine.validate_cold_chain: video_id must not "
                "be empty."
            )

        events = self._read_store("events")
        if video_id:
            events = [
                r for r in events if r.get("video_id") in (None, "", video_id)
            ]

        breach_types = {
            "temperature_breach",
            "cold_chain_breach",
            "temperature_exceeded",
        }
        breaches = [
            e
            for e in events
            if str(e.get("event_type", "")).strip().lower() in breach_types
        ]

        if not breaches:
            return {
                "is_valid": True,
                "breaches": [],
                "severity": "low",
            }

        severities = {str(e.get("severity", "low")).strip().lower() for e in breaches}
        if "critical" in severities:
            severity = "critical"
        elif "high" in severities:
            severity = "high"
        elif "medium" in severities:
            severity = "medium"
        else:
            severity = "low"

        return {
            "is_valid": False,
            "breaches": breaches,
            "severity": severity,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_store(self, name: str) -> list[dict[str, Any]]:
        """Read a CSV store defensively.

        Args:
            name: Store name (e.g. ``"detections"``).

        Returns:
            A list of row dictionaries (``[]`` when unavailable).
        """
        if self._storage is None:
            return []
        try:
            records = self._storage.read_csv_store(name)
        except Exception:
            logger.warning(
                "BusinessEngine: failed to read store '%s'.", name, exc_info=True
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


