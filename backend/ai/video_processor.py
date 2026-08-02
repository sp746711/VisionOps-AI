"""VisionOps AI — AI-level video processing.

Processes a video through the inference engine frame-by-frame,
optionally annotating frames with detections, and produces a processing
summary.  This is the **AI layer only** — it does **not**:

* save CSVs / JSON results directly
* generate dashboard KPIs
* trigger alerts
* send notifications
* implement API endpoints

Those responsibilities belong to the service/business/storage layers.

Resource safety
---------------
Every ``cv2.VideoCapture`` (and optional ``cv2.VideoWriter``) is released
deterministically in a ``finally`` block, even when processing fails or is
cancelled.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.exceptions import AIError, FileValidationError, ValidationError
from backend.ai.inference_engine import InferenceEngine
from backend.ai.utils.video_utils import (
    close_video,
    get_video_info,
    open_video,
    validate_video_file,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_FRAME_SKIP: int = 1
_DEFAULT_MAX_FRAMES: int = 0  # 0 == unlimited


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_frame_skip(value: int) -> int:
    """Validate a frame-skip value.

    Args:
        value: Number of frames to skip between processed frames (>= 1).

    Returns:
        Validated value.

    Raises:
        ValidationError: If the value is not a positive integer.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValidationError(
            f"frame_skip must be a positive integer, got {value!r}."
        )
    return value


def _validate_max_frames(value: int) -> int:
    """Validate a max-frames value.

    Args:
        value: Maximum frames to process (0 == no limit).

    Returns:
        Validated value.

    Raises:
        ValidationError: If the value is negative.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValidationError(
            f"max_frames must be a non-negative integer, got {value!r}."
        )
    return value


def _validate_ratio(value: float | int | None, name: str) -> float | None:
    """Validate an optional progress ratio in ``[0.0, 1.0]``.

    Args:
        value: Raw ratio value (or ``None``).
        name: Field name for error messages.

    Returns:
        Validated finite ratio, or ``None``.

    Raises:
        ValidationError: If the value is out of range or non-finite.
    """
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(
            f"{name} must be a number or None, got {value!r}."
        )
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValidationError(f"{name} must be finite, got {value!r}.")
    if number < 0.0 or number > 1.0:
        raise ValidationError(
            f"{name} must be in [0.0, 1.0], got {number}."
        )
    return number


# ---------------------------------------------------------------------------
# VideoProcessor
# ---------------------------------------------------------------------------


class VideoProcessor:
    """Processes a video through the inference engine.

    Args:
        engine: Optional :class:`InferenceEngine`.  When ``None`` one is
            created.
        use_mock: Test-only flag.  When ``True`` the engine is created in
            mock mode and video reading uses the extractor's mock path.
            Defaults to ``False``.
        frame_skip: Number of frames to skip between processed frames
            (default: 1 — every frame).
        max_frames: Maximum frames to process (default: 0 — no limit).
    """

    def __init__(
        self,
        engine: InferenceEngine | None = None,
        use_mock: bool = False,
        frame_skip: int = _DEFAULT_FRAME_SKIP,
        max_frames: int = _DEFAULT_MAX_FRAMES,
    ) -> None:
        """Initialise the video processor."""
        self._use_mock: bool = bool(use_mock)
        self._frame_skip: int = _validate_frame_skip(frame_skip)
        self._max_frames: int = _validate_max_frames(max_frames)

        self.engine: InferenceEngine = engine or InferenceEngine(
            use_mock=self._use_mock
        )

        self._processed_frames: int = 0
        self._total_detections: int = 0
        self._total_tracked: int = 0
        self._last_result: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_video(
        self,
        video_path: str | Path,
        *,
        output_path: str | Path | None = None,
        annotate: bool = True,
        frame_skip: int | None = None,
        max_frames: int | None = None,
        progress_callback: Any | None = None,
        cancel_check: Any | None = None,
    ) -> dict[str, Any]:
        """Process a video end-to-end.

        Args:
            video_path: Path to the video file.
            output_path: Optional path for an annotated output video.
            annotate: When ``True`` (and *output_path* is provided), draw
                bounding boxes/labels/track-IDs onto the output frames.
            frame_skip: Optional per-call override (>= 1).
            max_frames: Optional per-call override (0 == no limit).
            progress_callback: Optional ``(current, total, fraction)``
                callback invoked after each processed frame.
            cancel_check: Optional ``() -> bool`` callback; when ``True``,
                processing stops early.

        Returns:
            Processing summary dict with keys ``video_path``,
            ``total_frames``, ``processed_frames``, ``total_detections``,
            ``total_tracked``, ``fps``, ``frame_size``, ``output_path``,
            ``annotated``, ``cancelled``, and ``elapsed_seconds``.

        Raises:
            FileValidationError: If the video file is missing/empty.
            ValidationError: If arguments are invalid.
            AIError: If processing fails.
        """
        video_path = validate_video_file(video_path)
        frame_skip = _validate_frame_skip(
            frame_skip if frame_skip is not None else self._frame_skip
        )
        max_frames = _validate_max_frames(
            max_frames if max_frames is not None else self._max_frames
        )

        output: Path | None = None
        if output_path is not None:
            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)

        # Reset tracker before each video to prevent track-ID leakage.
        self.engine.reset_tracker()
        self.engine.reset_state()

        if self._use_mock:
            result = self._process_mock(
                video_path,
                output=output,
                annotate=annotate,
                frame_skip=frame_skip,
                max_frames=max_frames,
                cancel_check=cancel_check,
                progress_callback=progress_callback,
            )
            self._last_result = result
            return result

        cap = open_video(video_path)
        writer: Any | None = None
        try:
            info = get_video_info(cap)
            fps = float(info.get("fps", 0.0) or 30.0)
            width = int(info.get("width", 0))
            height = int(info.get("height", 0))
            total_frames = int(info.get("frame_count", 0))

            if output is not None:
                writer = self._create_writer(
                    output, fps=fps, width=width, height=height
                )

            processed = 0
            detections = 0
            tracked = 0
            frame_index = 0
            cancelled = False

            while True:
                if cancel_check is not None and cancel_check():
                    cancelled = True
                    logger.info(
                        "Processing cancelled for '%s' after %d frame(s).",
                        video_path.name,
                        processed,
                    )
                    break
                if max_frames > 0 and processed >= max_frames:
                    break

                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                if frame_index % frame_skip == 0:
                    result = self.engine.run_inference(
                        frame, frame_number=frame_index
                    )
                    frame_detections = result.get("detections", [])
                    detections += len(frame_detections)
                    tracked += sum(
                        1
                        for d in frame_detections
                        if d.get("track_id") is not None
                    )

                    if writer is not None and annotate:
                        from backend.ai.utils.drawing import draw_detections

                        annotated_frame = draw_detections(frame, frame_detections)
                        writer.write(annotated_frame)
                    elif writer is not None:
                        writer.write(frame)

                    processed += 1

                    if progress_callback is not None:
                        fraction = (
                            (processed / total_frames)
                            if total_frames > 0
                            else 0.0
                        )
                        progress_callback(processed, total_frames, fraction)

                frame_index += 1

            self._processed_frames = processed
            self._total_detections = detections
            self._total_tracked = tracked

            result_dict: dict[str, Any] = {
                "video_path": str(video_path),
                "total_frames": total_frames,
                "processed_frames": processed,
                "total_detections": detections,
                "total_tracked": tracked,
                "fps": fps,
                "frame_size": (width, height),
                "output_path": str(output) if output is not None else None,
                "annotated": annotate and output is not None,
                "cancelled": cancelled,
                "elapsed_seconds": 0.0,
            }
            self._last_result = result_dict
            return result_dict
        finally:
            close_video(cap)
            if writer is not None:
                try:
                    writer.release()
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("Failed to release video writer: %s", exc)
            logger.debug("Video processing resources released for '%s'.", video_path)

    # ------------------------------------------------------------------
    # Status / info
    # ------------------------------------------------------------------

    def get_processor_info(self) -> dict[str, Any]:
        """Return metadata about the processor.

        Returns:
            Dictionary with keys ``mock``, ``frame_skip``, ``max_frames``,
            ``engine``, ``processed_frames``, ``total_detections``, and
            ``total_tracked``.
        """
        return {
            "mock": self._use_mock,
            "frame_skip": self._frame_skip,
            "max_frames": self._max_frames,
            "engine": type(self.engine).__name__,
            "processed_frames": self._processed_frames,
            "total_detections": self._total_detections,
            "total_tracked": self._total_tracked,
        }

    def reset(self) -> None:
        """Reset processor counters and tracker state."""
        self.engine.reset_tracker()
        self._processed_frames = 0
        self._total_detections = 0
        self._total_tracked = 0
        self._last_result = None

    def __repr__(self) -> str:
        return (
            f"VideoProcessor(mock={self._use_mock}, "
            f"frame_skip={self._frame_skip}, max_frames={self._max_frames})"
        )

    # ------------------------------------------------------------------
    # Internal helpers (module-private)
    # ------------------------------------------------------------------

    def _process_mock(
        self,
        video_path: Path,
        *,
        output: Path | None,
        annotate: bool,
        frame_skip: int,
        max_frames: int,
        cancel_check: Any | None,
        progress_callback: Any | None,
    ) -> dict[str, Any]:
        """Produce a deterministic mock processing result (no OpenCV).

        Used when ``use_mock=True`` (unit tests / CI).  The video file is
        still validated (existence/extension/emptiness) but no frames are
        actually read or inferred — mock mode simply simulates the
        processing loop metadata.

        Returns:
            Processing summary dict with the same shape as the real path.
        """
        cancelled = False
        if cancel_check is not None and cancel_check():
            cancelled = True

        planned = list(range(0, 15, frame_skip))
        processed = max_frames if (max_frames > 0 and max_frames < len(planned)) else len(planned)
        if cancelled:
            processed = min(processed, 2)

        detections = 0
        tracked = 0

        self._processed_frames = processed
        self._total_detections = detections
        self._total_tracked = tracked

        if progress_callback is not None:
            progress_callback(processed, 15, processed / 15.0 if processed > 0 else 0.0)

        return {
            "video_path": str(video_path),
            "total_frames": 15,
            "processed_frames": processed,
            "total_detections": detections,
            "total_tracked": tracked,
            "fps": 30.0,
            "frame_size": (640, 480),
            "output_path": str(output) if output is not None else None,
            "annotated": annotate and output is not None,
            "cancelled": cancelled,
            "elapsed_seconds": 0.0,
        }

    def _create_writer(
        self,
        output_path: Path,
        *,
        fps: float,
        width: int,
        height: int,
    ) -> Any:
        """Create a :class:`cv2.VideoWriter` for annotated output.

        Args:
            output_path: Destination path.
            fps: Output video FPS.
            width: Output frame width.
            height: Output frame height.

        Returns:
            An opened :class:`cv2.VideoWriter`.

        Raises:
            AIError: If OpenCV is unavailable or the writer cannot be
                created.
        """
        try:
            import cv2
        except ImportError as exc:
            raise AIError(
                "OpenCV (opencv-python) is required for annotated video "
                "output but is not installed."
            ) from exc

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        try:
            writer = cv2.VideoWriter(
                str(output_path), fourcc, fps, (int(width), int(height))
            )
        except Exception as exc:
            raise AIError(
                f"Failed to create video writer for '{output_path}': {exc}"
            ) from exc

        if not writer.isOpened():
            writer.release()
            raise AIError(
                f"Failed to create video writer for '{output_path}' "
                "(codec unavailable?)."
            )
        return writer


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["VideoProcessor"]

