"""VisionOps AI — Analysis Service.

Provides business-logic orchestration for detection analysis, validation,
filtering, and aggregation of results after AI inference. Delegates all
low-level detection I/O to the storage layer and AI pipeline operations
to ``backend.ai``.

Responsibilities:
    - Detection orchestration
    - Detection validation
    - Detection filtering
    - Detection aggregation
    - Result persistence

Usage::

    from backend.services import AnalysisService

    service = AnalysisService()
    results = service.run_detection(video_id="vid_abc-123", detections=[...])
    validated = service.validate_detections(results)
    summary = service.aggregate_results(video_id="vid_abc-123")
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from backend.core.config import settings
from backend.exceptions import (
    ValidationError,
    StorageError,
    AnalyticsError,
)
from backend.storage import StorageService
from backend.utils.date_utils import now_utc
from backend.utils.id_generator import generate_uuid4
from backend.utils.math_utils import average, clamp, safe_division

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DETECTION_ID_PREFIX: str = "det_"
_DEFAULT_MIN_CONFIDENCE: float = 0.3
_DEFAULT_MAX_DETECTIONS: int = 10000
_ALLOWED_CLASSES: frozenset[str] = frozenset(
    {"person", "forklift", "pallet", "truck", "dock", "product"}
)

# ---------------------------------------------------------------------------
# AnalysisService
# ---------------------------------------------------------------------------


class AnalysisService:
    """Orchestrates detection analysis, validation, filtering, and
    aggregation.

    This service sits between the API layer and the storage/AI layers.
    It coordinates the flow of detection data from AI inference through
    validation, filtering, aggregation, and persistence — without
    implementing any low-level I/O or AI inference logic.

    Dependency injection is used for the storage layer to improve
    testability.

    Raises:
        ValidationError: If input arguments are invalid.
        StorageError: If storage operations fail.
        AnalyticsError: If analytics operations fail.
    """

    def __init__(
        self,
        storage: StorageService | None = None,
    ) -> None:
        """Initialise the analysis service.

        Args:
            storage: Injected ``StorageService`` instance. When ``None``,
                a default instance is created.
        """
        self._storage = storage or StorageService()
        logger.info(
            "AnalysisService initialised (storage=%s)",
            type(self._storage).__name__,
        )

    # ------------------------------------------------------------------
    # Detection Orchestration
    # ------------------------------------------------------------------

    def run_detection(
        self,
        video_id: str,
        detections: list[dict[str, Any]],
        source_frame: int | None = None,
    ) -> list[dict[str, Any]]:
        """Orchestrate detection processing: validate, filter, enrich,
        and persist detection results.

        This is the main entry point called after AI inference produces
        raw detections for a video.

        Args:
            video_id: Unique video identifier.
            detections: List of raw detection dictionaries. Each dict
                should contain at minimum ``class_name``, ``confidence``,
                and ``bbox`` keys.
            source_frame: Optional frame number this batch came from.

        Returns:
            List of enriched, validated, and persisted detection records.

        Raises:
            ValidationError: If *video_id* is empty or detections are
                invalid.
            StorageError: If persisting detections fails.
        """
        logger.info(
            "Running detection: video_id='%s', %d detections, frame=%s",
            video_id,
            len(detections),
            source_frame,
        )

        if not video_id:
            raise ValidationError("video_id must not be empty.")
        if not isinstance(detections, list):
            raise ValidationError(
                f"detections must be a list, got {type(detections).__name__}."
            )

        # Validate each detection
        validated = self.validate_detections(detections)

        # Filter low-confidence detections
        filtered = self.filter_detections(validated)

        # Enrich with metadata
        now = now_utc()
        enriched: list[dict[str, Any]] = []
        for det in filtered:
            enriched.append({
                "detection_id": f"{_DETECTION_ID_PREFIX}{generate_uuid4()}",
                "video_id": video_id,
                "frame_number": source_frame or 0,
                "class_name": det.get("class_name", "unknown"),
                "confidence": clamp(
                    float(det.get("confidence", 0.0)), 0.0, 1.0
                ),
                "bbox_x": float(det.get("bbox", [0, 0, 0, 0])[0]),
                "bbox_y": float(det.get("bbox", [0, 0, 0, 0])[1]),
                "bbox_w": float(det.get("bbox", [0, 0, 0, 0])[2]),
                "bbox_h": float(det.get("bbox", [0, 0, 0, 0])[3]),
                "track_id": det.get("track_id", ""),
                "created_at": now.isoformat(),
            })

        # Persist to CSV store
        try:
            self._storage.append_csv_store("detections", enriched)
        except StorageError as exc:
            logger.error(
                "Failed to persist %d detections for video '%s': %s",
                len(enriched),
                video_id,
                exc,
            )
            raise StorageError(
                f"Failed to persist detections for video '{video_id}': {exc}"
            ) from exc

        logger.info(
            "Detection completed: video_id='%s', %d detections persisted",
            video_id,
            len(enriched),
        )
        return enriched

    # ------------------------------------------------------------------
    # Detection Validation
    # ------------------------------------------------------------------

    def validate_detections(
        self,
        detections: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Validate a list of raw detection dictionaries.

        Checks for required fields, valid types, and acceptable ranges.
        Invalid detections are logged and excluded from the result.

        Args:
            detections: List of raw detection dictionaries.

        Returns:
            List of validated detection dictionaries. Invalid entries
            are omitted.
        """
        validated: list[dict[str, Any]] = []
        skipped: int = 0

        for idx, det in enumerate(detections):
            if not isinstance(det, dict):
                skipped += 1
                logger.debug("Detection at index %d is not a dict, skipping.", idx)
                continue

            # Check required fields
            class_name = det.get("class_name")
            confidence = det.get("confidence")
            bbox = det.get("bbox")

            if not class_name:
                skipped += 1
                logger.debug("Detection at index %d missing class_name.", idx)
                continue

            if confidence is None:
                skipped += 1
                logger.debug("Detection at index %d missing confidence.", idx)
                continue

            if not bbox or not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
                skipped += 1
                logger.debug(
                    "Detection at index %d has invalid bbox: %s", idx, bbox
                )
                continue

            # Validate confidence range
            try:
                conf_val = float(confidence)
                if conf_val < 0.0 or conf_val > 1.0:
                    skipped += 1
                    logger.debug(
                        "Detection at index %d has out-of-range confidence: %s",
                        idx,
                        confidence,
                    )
                    continue
            except (ValueError, TypeError):
                skipped += 1
                logger.debug(
                    "Detection at index %d has non-numeric confidence: %s",
                    idx,
                    confidence,
                )
                continue

            # Validate bbox values
            try:
                bbox_floats = [float(v) for v in bbox]
                if any(v < 0 for v in bbox_floats):
                    skipped += 1
                    logger.debug(
                        "Detection at index %d has negative bbox values: %s",
                        idx,
                        bbox,
                    )
                    continue
            except (ValueError, TypeError):
                skipped += 1
                logger.debug(
                    "Detection at index %d has non-numeric bbox values: %s",
                    idx,
                    bbox,
                )
                continue

            validated.append(det)

        if skipped:
            logger.warning(
                "Detection validation: %d valid, %d skipped",
                len(validated),
                skipped,
            )

        return validated

    # ------------------------------------------------------------------
    # Detection Filtering
    # ------------------------------------------------------------------

    def filter_detections(
        self,
        detections: list[dict[str, Any]],
        min_confidence: float | None = None,
        allowed_classes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Filter detections by confidence threshold and allowed classes.

        Args:
            detections: List of validated detection dictionaries.
            min_confidence: Minimum confidence threshold (default: from
                settings or 0.3).
            allowed_classes: List of allowed class names. If ``None``,
                all classes are allowed.

        Returns:
            Filtered list of detection dictionaries.
        """
        threshold = (
            min_confidence
            if min_confidence is not None
            else _DEFAULT_MIN_CONFIDENCE
        )
        threshold = clamp(threshold, 0.0, 1.0)

        allowed = (
            set(allowed_classes)
            if allowed_classes is not None
            else _ALLOWED_CLASSES
        )

        filtered: list[dict[str, Any]] = []

        for det in detections:
            conf = float(det.get("confidence", 0.0))
            class_name = det.get("class_name", "")

            if conf < threshold:
                continue
            if class_name not in allowed:
                continue

            filtered.append(det)

        logger.debug(
            "Detection filtering: %d -> %d (threshold=%.2f, allowed=%d classes)",
            len(detections),
            len(filtered),
            threshold,
            len(allowed),
        )
        return filtered

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def aggregate_results(
        self,
        video_id: str,
    ) -> dict[str, Any]:
        """Aggregate detection results for a video into a summary.

        Computes per-class counts, average confidence scores, and
        overall statistics.

        Args:
            video_id: Unique video identifier.

        Returns:
            Dictionary with aggregated results:
            - ``video_id``: The video identifier.
            - ``total_detections``: Total number of detection records.
            - ``unique_classes``: Number of distinct object classes.
            - ``class_counts``: Dictionary mapping class name to count.
            - ``average_confidence``: Overall average confidence.
            - ``class_avg_confidence``: Per-class average confidence.
            - ``detections_per_frame``: Average detections per frame.

        Raises:
            ValidationError: If *video_id* is empty.
            StorageError: If reading from the store fails.
        """
        if not video_id:
            raise ValidationError("video_id must not be empty.")

        try:
            records = self._storage.read_csv_store("detections")
        except StorageError as exc:
            raise StorageError(
                f"Failed to read detections for aggregation: {exc}"
            ) from exc

        # Filter records for this video
        video_detections = [
            r for r in records if r.get("video_id") == video_id
        ]

        if not video_detections:
            logger.info(
                "No detections found for video '%s'. Returning empty aggregation.",
                video_id,
            )
            return {
                "video_id": video_id,
                "total_detections": 0,
                "unique_classes": 0,
                "class_counts": {},
                "average_confidence": 0.0,
                "class_avg_confidence": {},
                "detections_per_frame": 0.0,
            }

        # Per-class counts
        class_counts: dict[str, int] = {}
        class_confidences: dict[str, list[float]] = {}
        frames_seen: set[str] = set()

        for det in video_detections:
            class_name = det.get("class_name", "unknown")
            class_counts[class_name] = class_counts.get(class_name, 0) + 1

            try:
                conf = float(det.get("confidence", 0.0))
            except (ValueError, TypeError):
                conf = 0.0

            class_confidences.setdefault(class_name, []).append(conf)

            frame = det.get("frame_number", "0")
            frames_seen.add(str(frame))

        # Compute averages
        total_dets = len(video_detections)
        total_confidence = sum(
            sum(confs) for confs in class_confidences.values()
        )
        avg_confidence = safe_division(total_confidence, total_dets, default=0.0)

        class_avg_confidence: dict[str, float] = {
            cls: safe_division(sum(confs), len(confs), default=0.0)
            for cls, confs in class_confidences.items()
        }

        frames_count = max(len(frames_seen), 1)
        dets_per_frame = safe_division(total_dets, frames_count, default=0.0)

        result: dict[str, Any] = {
            "video_id": video_id,
            "total_detections": total_dets,
            "unique_classes": len(class_counts),
            "class_counts": class_counts,
            "average_confidence": round(avg_confidence, 4),
            "class_avg_confidence": {
                cls: round(val, 4)
                for cls, val in class_avg_confidence.items()
            },
            "detections_per_frame": round(dets_per_frame, 2),
        }

        logger.info(
            "Aggregation completed for video '%s': %d detections, %d classes",
            video_id,
            total_dets,
            len(class_counts),
        )
        return result

    def get_detection_summary(
        self,
        video_id: str,
    ) -> dict[str, Any]:
        """Return a lightweight summary of detections for a video.

        Unlike ``aggregate_results``, this only reads pre-computed
        summary data from the JSON store if available, falling back to
        aggregation.

        Args:
            video_id: Unique video identifier.

        Returns:
            Summary dictionary with key counts and stats.
        """
        # Try to read pre-computed summary
        try:
            summary_data = self._storage.json_manager.read_summary()
            if isinstance(summary_data, dict):
                video_summary = summary_data.get("videos", {}).get(video_id)
                if video_summary:
                    logger.debug(
                        "Returning cached summary for video '%s'.",
                        video_id,
                    )
                    return video_summary  # type: ignore[return-value]
        except (StorageError, AnalyticsError):
            logger.debug(
                "No cached summary for video '%s', computing live.",
                video_id,
            )

        # Fall back to live aggregation
        return self.aggregate_results(video_id)

