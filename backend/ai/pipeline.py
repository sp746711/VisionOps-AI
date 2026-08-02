"""VisionOps AI — AI pipeline facade.

This module exposes the highest-level AI facade inside ``backend/ai``.
It coordinates frame extraction → detection → validation →
classification → tracking → optional annotation → normalized AI results
via the lower-level AI components.

Boundaries
----------
The pipeline keeps service/storage/business responsibilities OUT:

* It does **not** persist detections to CSV/JSON.
* It does **not** generate dashboard KPIs or business alerts.
* It does **not** trigger notifications.
* It does **not** implement API endpoints.

Those responsibilities belong to ``backend.services``,
``backend.business``, and ``backend.storage``.

The :class:`Pipeline` class (and the alias :class:`AIPipeline`) expose a
small, service-friendly API that :class:`~backend.services.video_service.VideoProcessingService`
can consume.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.exceptions import AIError, FileValidationError, ValidationError
from backend.ai.frame_extractor import FrameExtractor
from backend.ai.inference_engine import InferenceEngine
from backend.ai.video_processor import VideoProcessor
from backend.ai.utils.video_utils import validate_video_file

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PIPELINE_RESULT_KEYS: frozenset[str] = frozenset(
    {
        "status",
        "video_path",
        "total_frames",
        "processed_frames",
        "total_detections",
        "total_tracked",
        "detections",
        "output_path",
        "annotated",
        "cancelled",
        "elapsed_seconds",
        "message",
    }
)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class Pipeline:
    """Highest-level AI pipeline facade.

    Args:
        engine: Optional :class:`InferenceEngine`.  When ``None`` one is
            created.
        extractor: Optional :class:`FrameExtractor`.  When ``None`` one is
            created.
        processor: Optional :class:`VideoProcessor`.  When ``None`` one is
            created (backed by *engine*).
        use_mock: Test-only flag.  When ``True``, the underlying detector,
            tracker, extractor, and processor are created in mock mode so
            no heavy dependencies are loaded.  Defaults to ``False``.
    """

    def __init__(
        self,
        engine: InferenceEngine | None = None,
        extractor: FrameExtractor | None = None,
        processor: VideoProcessor | None = None,
        use_mock: bool = False,
    ) -> None:
        """Initialise the pipeline."""
        self._use_mock: bool = bool(use_mock)

        self.engine: InferenceEngine = engine or InferenceEngine(
            use_mock=self._use_mock
        )
        self.extractor: FrameExtractor = extractor or FrameExtractor(
            use_mock=self._use_mock
        )
        self.processor: VideoProcessor = processor or VideoProcessor(
            engine=self.engine,
            use_mock=self._use_mock,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        video_path: str | Path,
        *,
        params: dict[str, Any] | None = None,
        output_path: str | Path | None = None,
        annotate: bool = True,
        progress_callback: Any | None = None,
        cancel_check: Any | None = None,
    ) -> dict[str, Any]:
        """Run the complete AI pipeline over a video.

        Args:
            video_path: Path to the input video.
            params: Optional processing parameters:

                * ``frame_skip`` (int, >= 1): frames between processed
                  frames.
                * ``max_frames`` (int, >= 0): maximum frames to process
                  (0 == no limit).
                * ``confidence`` (float): detector confidence override.
                * ``iou`` (float): detector IoU override.
                * ``tracking`` (bool): override tracker enablement.
            output_path: Optional path for an annotated output video.
            annotate: Draw annotations on the output video (when
                *output_path* is set).
            progress_callback: Optional ``(current, total, fraction)``
                callback.
            cancel_check: Optional ``() -> bool`` cancellation callback.

        Returns:
            Processing result dict with keys:

            * ``status`` — ``"completed"`` or ``"cancelled"``.
            * ``video_path`` — input path (str).
            * ``total_frames`` — total video frames.
            * ``processed_frames`` — frames actually processed.
            * ``total_detections`` — total detections.
            * ``total_tracked`` — detections with track IDs.
            * ``detections`` — normalized detection dicts (flat list).
            * ``output_path`` — annotated output path or ``None``.
            * ``annotated`` — whether annotation was applied.
            * ``cancelled`` — whether processing was cancelled early.
            * ``elapsed_seconds`` — wall-clock processing time.
            * ``message`` — human-readable summary message.

        Raises:
            FileValidationError: If the video file is missing/empty.
            ValidationError: If parameters or video path are invalid.
            AIError: If a required AI dependency is unavailable.
        """
        del progress_callback  # reserved for future wiring
        video_path = validate_video_file(video_path)

        params = params or {}
        if not isinstance(params, dict):
            raise ValidationError(
                f"params must be a dict, got {type(params).__name__}."
            )

        frame_skip = params.get("frame_skip", 1)
        max_frames = params.get("max_frames", 0)

        # Validate numeric params early so malformed overrides fail fast.
        frame_skip = self._validate_int_param(
            frame_skip, name="frame_skip", min_value=1, allow_zero=False
        )
        max_frames = self._validate_int_param(
            max_frames, name="max_frames", min_value=0, allow_zero=True
        )

        if "confidence" in params:
            confidence = params["confidence"]
            if (
                isinstance(confidence, bool)
                or not isinstance(confidence, (int, float))
            ):
                raise ValidationError(
                    f"params['confidence'] must be a number, got {confidence!r}."
                )
            confidence = float(confidence)
            if not (0.0 <= confidence <= 1.0):
                raise ValidationError(
                    f"params['confidence'] must be in [0.0, 1.0], got "
                    f"{confidence}."
                )

        if "iou" in params:
            iou = params["iou"]
            if isinstance(iou, bool) or not isinstance(iou, (int, float)):
                raise ValidationError(
                    f"params['iou'] must be a number, got {iou!r}."
                )
            iou = float(iou)
            if not (0.0 <= iou <= 1.0):
                raise ValidationError(
                    f"params['iou'] must be in [0.0, 1.0], got {iou}."
                )

        tracking_override = params.get("tracking")

        # Apply overrides to the detector/tracker when present.
        self._apply_overrides(params)

        try:
            result = self.video_process(
                video_path=video_path,
                output_path=output_path,
                annotate=annotate,
                frame_skip=frame_skip,
                max_frames=max_frames,
                cancel_check=cancel_check,
            )
        except FileValidationError:
            raise
        except AIError:
            raise
        except Exception as exc:
            raise AIError(f"AI pipeline processing failed: {exc}") from exc

        # Re-attach the normalized detections and message.
        result["status"] = "cancelled" if result.get("cancelled") else "completed"
        result["message"] = (
            f"Processed {result.get('processed_frames', 0)} frame(s), "
            f"{result.get('total_detections', 0)} detection(s), "
            f"{result.get('total_tracked', 0)} tracked."
        )
        if tracking_override is not None and not tracking_override:
            # Tracking was explicitly disabled; reflect it in the message.
            result["message"] += " Tracking disabled by request."

        self._last_result = result
        return result

    def process_video(
        self,
        video_path: str | Path,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Async-style alias consumed by the video service.

        The actual heavy work is synchronous; this method exists to match
        the service-layer TODO contract::

            pipeline = AIPipeline()
            result = await pipeline.process_video(
                video_path=..., options=options or {},
            )

        Args:
            video_path: Path to the input video.
            options: Same options as :meth:`run`'s ``params``.

        Returns:
            Same result dict as :meth:`run`.
        """
        return self.run(video_path, params=options)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def video_process(
        self,
        *,
        video_path: str | Path,
        output_path: str | Path | None = None,
        annotate: bool = True,
        frame_skip: int = 1,
        max_frames: int = 0,
        cancel_check: Any | None = None,
    ) -> dict[str, Any]:
        """Delegate actual video processing to the VideoProcessor.

        This method exists so subclasses can override the delegation
        point while the facade (param normalization, result shaping)
        stays consistent.

        Returns:
            Raw VideoProcessor result dict.
        """
        return self.processor.process_video(
            video_path,
            output_path=output_path,
            annotate=annotate,
            frame_skip=frame_skip,
            max_frames=max_frames,
            cancel_check=cancel_check,
        )

    @staticmethod
    def _validate_int_param(
        value: Any,
        *,
        name: str,
        min_value: int,
        allow_zero: bool,
    ) -> int:
        """Validate an integer pipeline parameter.

        Args:
            value: Raw value.
            name: Parameter name for error messages.
            min_value: Minimum allowed value (inclusive).
            allow_zero: Whether *min_value* ``0`` is allowed.

        Returns:
            Validated int.

        Raises:
            ValidationError: If the value is invalid.
        """
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValidationError(
                f"params['{name}'] must be an int, got {value!r}."
            )
        if value < min_value or (value == 0 and not allow_zero):
            lower = min_value or 1
            raise ValidationError(
                f"params['{name}'] must be >= {lower}, got {value}."
            )
        return value

    def _apply_overrides(self, params: dict[str, Any]) -> None:
        """Apply detector/tracker parameter overrides (when present).

        Args:
            params: Pipeline parameter dict.
        """
        # The detector uses threshold overrides when provided.
        if "confidence" in params:
            detector = getattr(self.engine, "detector", None)
            if detector is not None and hasattr(detector, "_confidence_threshold"):
                detector._confidence_threshold = float(params["confidence"])  # type: ignore[assignment]
        if "iou" in params:
            detector = getattr(self.engine, "detector", None)
            if detector is not None and hasattr(detector, "_iou_threshold"):
                detector._iou_threshold = float(params["iou"])  # type: ignore[assignment]
        if "tracking" in params:
            tracker = getattr(self.engine, "tracker", None)
            if tracker is not None and hasattr(tracker, "_enabled"):
                tracker._enabled = bool(params["tracking"])  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Status / info
    # ------------------------------------------------------------------

    def get_pipeline_info(self) -> dict[str, Any]:
        """Return metadata about the pipeline.

        Returns:
            Dictionary with keys ``name``, ``mock``, ``engine``,
            ``extractor``, and ``processor``.
        """
        return {
            "name": "Pipeline",
            "mock": self._use_mock,
            "engine": type(self.engine).__name__,
            "extractor": type(self.extractor).__name__,
            "processor": type(self.processor).__name__,
        }

    def reset(self) -> None:
        """Reset all sub-components to a clean state."""
        self.engine.reset_state()
        self.extractor.reset()
        self.processor.reset()
        self._last_result = None

    def __repr__(self) -> str:
        return f"Pipeline(mock={self._use_mock})"


# ---------------------------------------------------------------------------
# AIPipeline alias (service-facing name)
# ---------------------------------------------------------------------------


class AIPipeline(Pipeline):
    """Alias for :class:`Pipeline` used by the service layer.

    The ``backend.services.video_service.VideoProcessingService`` TODO
    references ``from backend.ai.pipeline import AIPipeline``; this alias
    keeps that contract intact while preserving a single implementation.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Forward all arguments to :class:`Pipeline`."""
        super().__init__(*args, **kwargs)


# ---------------------------------------------------------------------------
# Convenience helper
# ---------------------------------------------------------------------------


def run_pipeline(
    video_path: str | Path,
    *,
    use_mock: bool = False,
    options: dict[str, Any] | None = None,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run the AI pipeline over a video with a fresh instance.

    Args:
        video_path: Path to the input video.
        use_mock: Test-only flag.
        options: Processing parameters (same keys as :meth:`Pipeline.run`).
        output_path: Optional annotated output path.

    Returns:
        Processing result dict (see :meth:`Pipeline.run`).

    Raises:
        FileValidationError: If the video file is missing/empty.
        ValidationError: If parameters are invalid.
        AIError: If a required AI dependency is unavailable.
    """
    pipeline = Pipeline(use_mock=use_mock)
    return pipeline.run(
        video_path,
        params=options,
        output_path=output_path,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["Pipeline", "AIPipeline", "run_pipeline"]

