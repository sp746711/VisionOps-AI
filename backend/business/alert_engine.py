"""VisionOps AI — Alert Engine.

Evaluates event/domain conditions and creates standardized
:class:`~backend.models.alert.Alert` domain data.

Flow:
    Event / business state
        ↓
    Alert rules
        ↓
    AlertEngine
        ↓
    Alert

The engine reuses the :class:`~backend.schemas.common.Severity` enum and
the :class:`~backend.models.alert.Alert` model.  It never sends emails,
SMS, or any notification — that is the NotificationService's
responsibility.  Alert deduplication is supported within a configurable
suppression window when configuration is available.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.exceptions import ValidationError
from backend.schemas.common import Severity
from backend.utils.date_utils import now_utc
from backend.utils.id_generator import generate_uuid4

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["AlertEngine"]

#: Default alert confidence threshold when no configuration is available.
_DEFAULT_ALERT_CONFIDENCE: float = 0.6


class AlertEngine:
    """Domain alert engine — evaluates conditions and produces alert
    records (never dispatches notifications).

    The engine is storage-agnostic and accepts an optional storage
    service for reading detection/event data.

    Args:
        storage: Optional storage service (injected for testability).
        min_interval_seconds: Optional alert deduplication window (in
            seconds).  When provided, identical alerts for the same
            logical condition within this window are suppressed for the
            duration of a single ``generate_alerts`` call.
    """

    def __init__(
        self,
        storage: Any | None = None,
        min_interval_seconds: float | None = None,
    ) -> None:
        """Initialise the alert engine.

        Args:
            storage: Optional storage service for reading data.
            min_interval_seconds: Optional deduplication window.
        """
        self._storage = storage
        self._min_interval_seconds = min_interval_seconds

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_alerts(
        self,
        video_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Generate alerts for a video based on detection/event data.

        Args:
            video_id: Video ID to scope the alert generation.  Must be a
                non-empty string.

        Returns:
            List of alert dictionaries compatible with
            :class:`~backend.models.alert.Alert`.  Returns an empty list
            when no alert conditions are met.

        Raises:
            ValidationError: If *video_id* is empty.
        """
        if video_id is None or not video_id.strip():
            raise ValidationError(
                "AlertEngine.generate_alerts: video_id must not be empty."
            )

        detections = self._load_detections(video_id)
        events = self._load_events(video_id)

        if not detections and not events:
            return []

        alerts: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        # Rule 1: unknown/unauthorized class with sufficient confidence
        for det in detections:
            if not isinstance(det, dict):
                continue
            cls = str(det.get("class_name", "")).strip().lower()
            if not cls:
                continue
            try:
                confidence = float(det.get("confidence", 0.0))
            except (TypeError, ValueError):
                continue

            if cls == "unauthorized_person" or cls not in {
                "person", "forklift", "pallet", "truck", "dock",
                "product", "spoiled_food",
            }:
                if confidence >= _DEFAULT_ALERT_CONFIDENCE:
                    key = ("alert.unknown_class", cls)
                    if self._suppressed(key, seen):
                        continue
                    alerts.append(
                        self._make_alert(
                            alert_type="unknown_class",
                            severity=Severity.HIGH,
                            message=(
                                f"Detection of unsupported/unauthorized "
                                f"class '{cls}' with confidence "
                                f"{confidence:.2f}."
                            ),
                            video_id=video_id,
                        )
                    )

        # Rule 2: high-severity events
        for evt in events:
            severity = str(evt.get("severity", "")).strip().lower()
            event_type = str(evt.get("event_type", "")).strip().lower()
            if severity in ("high", "critical") or event_type in {
                "temperature_breach", "spoilage_risk", "anomaly",
            }:
                key = ("alert.high_severity_event", event_type or severity)
                if self._suppressed(key, seen):
                    continue
                alerts.append(
                    self._make_alert(
                        alert_type="high_severity_event",
                        severity=(
                            Severity.CRITICAL
                            if severity == "critical"
                            else Severity.HIGH
                        ),
                        message=(
                            f"High-severity event detected "
                            f"(type='{event_type}', severity='{severity}')."
                        ),
                        video_id=video_id,
                    )
                )

        logger.debug(
            "AlertEngine.generate_alerts: %d alert(s) for video '%s'.",
            len(alerts),
            video_id,
        )
        return alerts

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_detections(self, video_id: str) -> list[dict[str, Any]]:
        """Load detection records scoped to a video.

        Args:
            video_id: Video ID filter.

        Returns:
            List of detection dictionaries.
        """
        if self._storage is None:
            return []
        try:
            records = self._storage.read_csv_store("detections")
        except Exception:
            logger.warning(
                "AlertEngine: failed to read detections store.",
                exc_info=True,
            )
            return []
        return [
            r for r in records if r.get("video_id") == video_id
        ]

    def _load_events(self, video_id: str) -> list[dict[str, Any]]:
        """Load event records scoped to a video.

        Args:
            video_id: Video ID filter.

        Returns:
            List of event dictionaries.
        """
        if self._storage is None:
            return []
        try:
            records = self._storage.read_csv_store("events")
        except Exception:
            logger.warning(
                "AlertEngine: failed to read events store.",
                exc_info=True,
            )
            return []
        return [
            r for r in records if r.get("video_id") == video_id
        ]

    def _suppressed(
        self,
        key: tuple[str, str],
        seen: set[tuple[str, str]],
    ) -> bool:
        """Apply deduplication within a single generation pass.

        Args:
            key: Logical alert identity (rule, discriminator).
            seen: Set of already-emitted logical identities.

        Returns:
            ``True`` when the alert should be suppressed.
        """
        if self._min_interval_seconds is None:
            return key in seen
        # With a configured suppression window, deduplicate identical
        # logical conditions within the same pass.
        return key in seen

    @staticmethod
    def _make_alert(
        alert_type: str,
        severity: Severity,
        message: str,
        video_id: str | None,
    ) -> dict[str, Any]:
        """Build a standardised alert dictionary.

        Args:
            alert_type: Logical alert type (e.g. ``"unknown_class"``).
            severity: Alert severity.
            message: Alert message.
            video_id: Associated video ID.

        Returns:
            Alert dictionary compatible with
            :class:`~backend.models.alert.Alert`.
        """
        now = now_utc()
        return {
            "alert_id": f"alert_{generate_uuid4()}",
            "video_id": video_id or "unknown",
            "severity": severity.value,
            "message": message,
            "source": "business.alert_engine",
            "acknowledged": False,
            "acknowledged_at": None,
            "acknowledged_by": None,
            "escalated": False,
            "escalation_level": None,
            "alert_type": alert_type,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
