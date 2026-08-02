"""VisionOps AI — Event Engine.

Converts meaningful domain conditions into standardized
:class:`~backend.models.event.Event` domain data.

Flow:
    Detections / Tracking
        ↓
    Rules
        ↓
    EventEngine
        ↓
    Event

The engine reads detection data (via the injected storage service),
evaluates applicable rules, and produces event records.  It does *not*
persist events directly — that responsibility belongs to the service
layer.  Returns a list of event dictionaries (or
:class:`~backend.models.event.Event` objects) for the caller to
persist if desired.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.exceptions import ValidationError
from backend.utils.date_utils import now_utc
from backend.utils.id_generator import generate_uuid4

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["EventEngine"]


class EventEngine:
    """Domain event engine — converts detection/rule conditions into
    structured event records.

    The engine is storage-agnostic and receives an optional storage
    service for reading detection/event data.  It never persists events
    directly; it returns event data for the caller.

    Args:
        storage: Optional storage service for reading detection/event
            data.  When ``None``, the engine operates on explicitly
            provided data only.
    """

    def __init__(self, storage: Any | None = None) -> None:
        """Initialise the event engine.

        Args:
            storage: Optional storage service (injected for testability).
        """
        self._storage = storage

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_events(
        self,
        video_id: str | None = None,
        detections: list[Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Process detections and generate event records.

        Reads detections from storage (when *video_id* is provided and
        *detections* is ``None``) or uses the supplied *detections*
        directly.  Each event is returned as a dictionary compatible
        with the :class:`~backend.models.event.Event` model.

        Args:
            video_id: Optional video ID to scope the processing.
            detections: Optional detection list (dicts or
                :class:`~backend.models.detection.Detection` objects).
                When provided, *video_id* is used as metadata.

        Returns:
            List of event dictionaries (never ``None``).  Returns an
            empty list when no conditions warrant an event.

        Raises:
            ValidationError: If *video_id* is provided but empty.
        """
        if video_id is not None and not video_id.strip():
            raise ValidationError(
                "EventEngine.process_events: video_id must not be empty."
            )

        # Load detections from storage if not explicitly provided
        if detections is None:
            detections = self._load_detections(video_id)

        if not detections:
            return []

        events: list[dict[str, Any]] = []
        now = now_utc()

        # Generate events based on detection patterns
        # 1. Count events per-class when a significant number exist
        class_counts: dict[str, int] = {}
        for det in detections:
            if isinstance(det, dict):
                cls = str(det.get("class_name", "")).strip().lower()
            else:
                cls = str(getattr(det, "class_name", "")).strip().lower()
            if cls:
                class_counts[cls] = class_counts.get(cls, 0) + 1

        if class_counts:
            # Event: detection_summary — per-class detection occurrence
            for cls, count in sorted(class_counts.items()):
                # Only create an event for classes with meaningful presence
                if count > 0:
                    events.append(
                        self._make_event(
                            event_type=f"detection_{cls}",
                            description=(
                                f"{count} detection(s) of class '{cls}'."
                            ),
                            severity="low",
                            video_id=video_id or "unknown",
                            source="business.event_engine",
                            timestamp=now,
                        )
                    )

        logger.debug(
            "EventEngine.process_events: %d event(s) from %d detection(s) "
            "(video_id=%s)",
            len(events),
            len(detections),
            video_id or "N/A",
        )
        return events

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_detections(
        self, video_id: str | None
    ) -> list[dict[str, Any]]:
        """Load detection records from the storage service.

        Args:
            video_id: Optional video filter.

        Returns:
            List of detection dictionaries.
        """
        if self._storage is None:
            return []
        try:
            records = self._storage.read_csv_store("detections")
        except Exception:
            logger.warning(
                "EventEngine: failed to read detections store.", exc_info=True
            )
            return []

        if video_id:
            records = [
                r for r in records if r.get("video_id") == video_id
            ]
        return records

    @staticmethod
    def _make_event(
        event_type: str,
        description: str,
        severity: str = "low",
        video_id: str | None = None,
        source: str | None = None,
        timestamp: Any | None = None,
    ) -> dict[str, Any]:
        """Build a standardised event dictionary.

        Args:
            event_type: Machine-readable event type.
            description: Human-readable description.
            severity: Severity string (``"low"``, ``"medium"``,
                ``"high"``, ``"critical"``).
            video_id: Associated video ID.
            source: Event source identifier.
            timestamp: Event timestamp (UTC).

        Returns:
            Event dictionary compatible with
            :class:`~backend.models.event.Event`.
        """
        ts = timestamp or now_utc()
        return {
            "event_id": f"evt_{generate_uuid4()}",
            "video_id": video_id or "unknown",
            "event_type": event_type,
            "description": description,
            "severity": severity,
            "source": source or "business.event_engine",
            "created_at": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
            "updated_at": None,
        }
