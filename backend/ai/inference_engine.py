"""VisionOps AI — Inference engine (AI orchestration layer).

The inference engine sits **below** the application service layer and
orchestrates the AI components for a single frame or a batch of frames:

    Frame
      ↓
    YOLODetector
      ↓
    DetectionValidator
      ↓
    ObjectClassifier
      ↓
    ByteTrackTracker
      ↓
    Normalized AI result

It does **not** implement:

* API logic / HTTP handling
* storage persistence
* business alerts
* analytics KPIs
* dashboard calculations

These responsibilities belong to upstream layers.

Design
------
Components are injected :class:`~backend.ai.detection_validator.DetectionValidator`
is created internally unless provided, while hard-to-mock heavy components
(detector/tracker/classifier) are injectable.  Each engine instance owns
its tracker state so concurrent videos never share tracking state.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.ai.yolo_detector import YOLODetector
from backend.ai.detection_validator import DetectionValidator
from backend.ai.object_classifier import ObjectClassifier
from backend.ai.bytetrack_tracker import ByteTrackTracker
from backend.exceptions import AIError, ValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_DETECTOR_USE_MOCK: bool = False
_DEFAULT_TRACKER_USE_MOCK: bool = False


# ---------------------------------------------------------------------------
# InferenceEngine
# ---------------------------------------------------------------------------


class InferenceEngine:
    """Coordinates detector, validator, classifier, and tracker.

    Args:
        detector: Optional :class:`YOLODetector`.  When ``None`` one is
            created.
        tracker: Optional :class:`ByteTrackTracker`.  When ``None`` one is
            created honoring ``settings.BYTETRACK_ENABLED``.
        classifier: Optional :class:`ObjectClassifier`.  When ``None`` one
            is created.
        validator: Optional :class:`DetectionValidator`.  When ``None``
            one is created.
        use_mock: Test-only flag.  When ``True``, the detector and tracker
            are instantiated in mock mode (no heavy dependencies loaded).
            Defaults to ``False``.
    """

    def __init__(
        self,
        detector: YOLODetector | None = None,
        tracker: ByteTrackTracker | None = None,
        classifier: ObjectClassifier | None = None,
        validator: DetectionValidator | None = None,
        use_mock: bool = False,
    ) -> None:
        """Initialise the inference engine with the given components."""
        self._use_mock: bool = bool(use_mock)

        self.detector: YOLODetector = detector or YOLODetector(
            use_mock=self._use_mock or _DEFAULT_DETECTOR_USE_MOCK
        )
        self.tracker: ByteTrackTracker = tracker or ByteTrackTracker(
            use_mock=self._use_mock or _DEFAULT_TRACKER_USE_MOCK
        )
        self.classifier: ObjectClassifier = classifier or ObjectClassifier()
        self.validator: DetectionValidator = validator or DetectionValidator()

        self._total_frames_processed: int = 0
        self._total_detections: int = 0
        self._total_tracked: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_inference(
        self,
        frame: Any,
        *,
        frame_number: int | None = None,
        apply_tracking: bool | None = None,
    ) -> dict[str, Any]:
        """Run the full inference pipeline on a single frame.

        Args:
            frame: Image frame (BGR ``HxWx3`` uint8 array).
            frame_number: Optional zero-based frame number (for metadata
                in the returned result).
            apply_tracking: Override for tracker enablement.  When
                ``None``, the tracker's own configuration is honored.

        Returns:
            A normalized AI result dict::

                {
                    "frame_number": int | None,
                    "detections": [ {class_name, confidence, bbox, track_id}, ... ],
                    "tracking_applied": bool,
                    "count": int,
                }

        Raises:
            AIError: If inference fails.
            ValidationError: If *frame* is invalid.
        """
        if frame_number is not None:
            if isinstance(frame_number, bool) or not isinstance(frame_number, int):
                raise ValidationError(
                    f"frame_number must be an integer or None, got {frame_number!r}."
                )
            if frame_number < 0:
                raise ValidationError(
                    f"frame_number must be non-negative, got {frame_number}."
                )

        raw_detections = self.detector.detect(frame)

        validated = self.validator.validate_batch_strict(raw_detections)
        normalized = self.classifier.classify(validated)

        tracking_applied = False
        if apply_tracking is not None:
            tracking_applied = apply_tracking
            if tracking_applied:
                normalized = self.tracker.update(normalized)
        elif self.tracker.is_enabled():
            tracking_applied = True
            normalized = self.tracker.update(normalized)

        self._total_frames_processed += 1
        self._total_detections += len(validated)
        self._total_tracked += sum(
            1 for d in normalized if d.get("track_id") is not None
        )

        return {
            "frame_number": frame_number,
            "detections": normalized,
            "tracking_applied": tracking_applied,
            "count": len(normalized),
        }

    def run_inference_batch(
        self,
        frames: list[Any],
        *,
        frame_numbers: list[int] | None = None,
        apply_tracking: bool | None = None,
    ) -> list[dict[str, Any]]:
        """Run the inference pipeline on a batch of frames.

        Args:
            frames: List of image frames.
            frame_numbers: Optional list of frame numbers parallel to
                *frames*.
            apply_tracking: Optional tracker enablement override.

        Returns:
            List of normalized AI result dicts, one per frame.

        Raises:
            AIError: If inference fails.
            ValidationError: If *frames* is not a list or lengths mismatch.
        """
        if not isinstance(frames, list):
            raise ValidationError(
                f"frames must be a list, got {type(frames).__name__}."
            )
        if frame_numbers is not None and len(frame_numbers) != len(frames):
            raise ValidationError(
                "frame_numbers length must match frames length "
                f"({len(frame_numbers)} != {len(frames)})."
            )

        results: list[dict[str, Any]] = []
        for idx, frame in enumerate(frames):
            frame_number = frame_numbers[idx] if frame_numbers is not None else None
            results.append(
                self.run_inference(
                    frame,
                    frame_number=frame_number,
                    apply_tracking=apply_tracking,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Tracker lifecycle
    # ------------------------------------------------------------------

    def reset_tracker(self) -> None:
        """Reset tracker state.

        Must be called between independent videos to guarantee no track-ID
        leakage across videos.
        """
        self.tracker.reset()
        logger.debug("InferenceEngine tracker reset.")

    def reset_state(self) -> None:
        """Reset tracker state and internal counters.

        Call between independent videos/video jobs to guarantee a clean
        tracking state and accurate per-video statistics.
        """
        self.reset_tracker()
        self._total_frames_processed = 0
        self._total_detections = 0
        self._total_tracked = 0
        logger.debug("InferenceEngine state reset.")

    # ------------------------------------------------------------------
    # Status / info
    # ------------------------------------------------------------------

    def get_engine_info(self) -> dict[str, Any]:
        """Return metadata about the engine and its components.

        Returns:
            Dictionary with keys ``name``, ``use_mock``,
            ``detector``, ``tracker``, ``classifier``, ``validator``, and
            totals.
        """
        return {
            "name": "InferenceEngine",
            "use_mock": self._use_mock,
            "detector": self.detector.get_model_info()
            if hasattr(self.detector, "get_model_info")
            else type(self.detector).__name__,
            "tracker": self.tracker.get_tracker_info()
            if hasattr(self.tracker, "get_tracker_info")
            else type(self.tracker).__name__,
            "classifier": type(self.classifier).__name__,
            "validator": type(self.validator).__name__,
            "total_frames_processed": self._total_frames_processed,
            "total_detections": self._total_detections,
            "total_tracked": self._total_tracked,
        }

    def __repr__(self) -> str:
        return (
            f"InferenceEngine(mock={self._use_mock}, "
            f"detector={type(self.detector).__name__}, "
            f"tracker={type(self.tracker).__name__})"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["InferenceEngine"]

