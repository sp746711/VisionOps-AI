"""VisionOps AI — Frame extraction from videos.

Extracts frames from video files with configurable frame stepping,
FPS-aware extraction, and deterministic OpenCV resource cleanup.

Resource safety
---------------
Every ``cv2.VideoCapture`` opened by this module is guaranteed to be
released via ``try/finally`` / context-manager style cleanup, even when
extraction fails or is cancelled mid-way.

Temporal contract
-----------------
Frames are returned in order with their zero-based frame indices and
timestamps (seconds)::

    {"frame": numpy.ndarray(H, W, 3), "frame_number": int,
     "timestamp": float}
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterator
from collections.abc import Callable

from backend.exceptions import AIError, FileValidationError, ValidationError
from backend.ai.utils.image_utils import validate_image
from backend.ai.utils.video_utils import (
    SUPPORTED_VIDEO_EXTENSIONS,
    close_video,
    get_video_info,
    is_supported_video,
    open_video,
    validate_video_file,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _validate_interval(interval: int) -> int:
    """Validate a frame interval.

    Args:
        interval: Frames to skip between extracted frames (>= 1).

    Returns:
        Validated interval.

    Raises:
        ValidationError: If the interval is not a positive integer.
    """
    if isinstance(interval, bool) or not isinstance(interval, int) or interval < 1:
        raise ValidationError(
            f"interval must be a positive integer, got {interval!r}."
        )
    return interval


def _normalize_limit(limit: int | None) -> int | None:
    """Validate an optional extraction limit.

    Args:
        limit: Maximum frames to extract, or ``None`` for no limit.

    Returns:
        Validated limit.

    Raises:
        ValidationError: If the limit is not a positive integer.
    """
    if limit is None:
        return None
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValidationError(
            f"limit must be a positive integer or None, got {limit!r}."
        )
    return limit


def _resolve_path(video_path: str | Path | None) -> Path:
    """Coerce a ``video_path`` argument into a :class:`pathlib.Path`.

    Args:
        video_path: Raw video path.  When ``None``, the configured
            ``settings.YOLO_MODEL_PATH`` parent is used as a fallback
            base — this is practically never used by callers, but keeps
            the default-argument contract simple.

    Returns:
        The path as a :class:`pathlib.Path`.
    """
    if video_path is None:
        raise ValidationError(
            "video_path is required for frame extraction."
        )
    return Path(video_path)


# ---------------------------------------------------------------------------
# FrameExtractor
# ---------------------------------------------------------------------------


class FrameExtractor:
    """Extracts frames from video files.

    Args:
        interval: Number of frames to skip between extracted frames
            (default: 1 — every frame).
        limit: Maximum number of frames to extract (default: ``None`` —
            no limit).
        use_mock: Test-only flag.  When ``True``, a lightweight mock
            frame is produced for each scheduled frame index (used by
            unit tests / CI without OpenCV).  Defaults to ``False``.
    """

    def __init__(
        self,
        interval: int = 1,
        limit: int | None = None,
        use_mock: bool = False,
    ) -> None:
        """Initialise the frame extractor."""
        self._interval: int = _validate_interval(interval)
        self._limit: int | None = _normalize_limit(limit)
        self._use_mock: bool = bool(use_mock)

        self._frames_extracted: int = 0
        self._last_error: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_frames(
        self,
        video_path: str | Path | None = None,
        *,
        interval: int | None = None,
        limit: int | None = None,
        use_mock: bool | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract frames from a video file into memory.

        Args:
            video_path: Path to the video file.
            interval: Optional per-call interval override.
            limit: Optional per-call limit override.
            use_mock: Optional per-call mock-override.
            cancel_check: Optional ``() -> bool`` callback; when it
                returns ``True``, extraction stops early.

        Returns:
            List of frame dicts::

                {"frame": ndarray, "frame_number": int, "timestamp": float}

        Raises:
            ValidationError: If the file extension is unsupported.
            FileValidationError: If the file is missing or empty.
            AIError: If OpenCV is unavailable or the video cannot be read.
        """
        video_path = _resolve_path(video_path)
        use_mock = use_mock if use_mock is not None else self._use_mock
        interval = _validate_interval(interval if interval is not None else self._interval)
        limit = _normalize_limit(limit if limit is not None else self._limit)

        # Validate file extension/existence/emptiness first.
        validate_video_file(video_path)

        if use_mock:
            return self._extract_mock(video_path, interval=interval, limit=limit)

        frames = self._extract_real(
            video_path, interval=interval, limit=limit, cancel_check=cancel_check
        )
        self._frames_extracted = len(frames)
        return frames

    def iter_frames(
        self,
        video_path: str | Path | None = None,
        *,
        interval: int | None = None,
        limit: int | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield frames lazily from a video (generator).

        The underlying ``cv2.VideoCapture`` is released deterministically
        when the generator is exhausted, closed, or an exception
        propagates.

        Args:
            video_path: Path to the video file.
            interval: Optional interval override.
            limit: Optional limit override.
            cancel_check: Optional cancellation callback.

        Yields:
            Frame dicts (``frame``, ``frame_number``, ``timestamp``).

        Raises:
            ValidationError: If the file extension is unsupported.
            FileValidationError: If the file is missing or empty.
            AIError: If OpenCV is unavailable or the video cannot be read.
        """
        video_path = _resolve_path(video_path)

        interval = _validate_interval(interval if interval is not None else self._interval)
        limit = _normalize_limit(limit if limit is not None else self._limit)

        validate_video_file(video_path)

        if self._use_mock:
            for frame in self._extract_mock(
                video_path, interval=interval, limit=limit
            ):
                yield frame
            return

        cap = open_video(video_path)
        try:
            info = get_video_info(cap)
            fps = info.get("fps", 0.0) or 30.0
            frame_index = 0
            extracted = 0

            while True:
                if cancel_check is not None and cancel_check():
                    logger.info(
                        "Frame extraction cancelled for '%s' after %d frame(s).",
                        video_path.name,
                        extracted,
                    )
                    break
                if limit is not None and extracted >= limit:
                    break

                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                if frame_index % interval == 0:
                    yield {
                        "frame": frame,
                        "frame_number": frame_index,
                        "timestamp": self._timestamp(frame_index, fps),
                    }
                    extracted += 1

                frame_index += 1
        finally:
            close_video(cap)
            logger.debug("VideoCapture released for '%s'.", video_path.name)

    # ------------------------------------------------------------------
    # Frame count
    # ------------------------------------------------------------------

    def get_frame_count(
        self,
        video_path: str | Path | None = None,
        *,
        use_mock: bool | None = None,
    ) -> int:
        """Return the total frame count of a video.

        Args:
            video_path: Path to the video file.
            use_mock: Optional per-call mock-override.

        Returns:
            Total frame count (>= 0).  In mock mode a small deterministic
            count (> 0) is returned.

        Raises:
            FileValidationError: If the file is missing or empty.
            AIError: If OpenCV is unavailable.
        """
        video_path = _resolve_path(video_path)
        use_mock = use_mock if use_mock is not None else self._use_mock

        validate_video_file(video_path)

        if use_mock:
            return 15

        cap = open_video(video_path)
        try:
            info = get_video_info(cap)
            return int(info.get("frame_count", 0))
        finally:
            close_video(cap)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamp(frame_index: int, fps: float) -> float:
        """Return a frame timestamp in seconds.

        Args:
            frame_index: Zero-based frame index.
            fps: Frames per second (must be positive and finite).

        Returns:
            Timestamp in seconds.

        Raises:
            ValidationError: If *fps* is invalid.
        """
        if isinstance(fps, bool) or not isinstance(fps, (int, float)):
            raise ValidationError(f"fps must be a number, got {fps!r}.")
        if fps <= 0.0:
            raise ValidationError(f"fps must be positive, got {fps!r}.")
        fps_value = float(fps)
        if fps_value != fps_value or fps_value in (float("inf"), float("-inf")):
            raise ValidationError(f"fps must be finite, got {fps!r}.")
        return round(float(frame_index) / fps_value, 4)

    def _extract_mock(
        self,
        video_path: Path,
        *,
        interval: int,
        limit: int | None,
    ) -> list[dict[str, Any]]:
        """Produce deterministic mock frames without a real video.

        Mock frames are lightweight dictionaries with a ``frame`` value of
        ``None`` — **no fabricated detection content** is created.

        Returns:
            List of mock frame dicts.
        """
        del video_path
        total = 15
        frames: list[dict[str, Any]] = []
        for index in range(0, total, interval):
            if limit is not None and len(frames) >= limit:
                break
            frames.append(
                {
                    "frame": None,
                    "frame_number": index,
                    "timestamp": self._timestamp(index, 30.0),
                }
            )
        self._frames_extracted = len(frames)
        return frames

    def _extract_real(
        self,
        video_path: Path,
        *,
        interval: int,
        limit: int | None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> list[dict[str, Any]]:
        """Extract frames from a real video into memory.

        Args:
            video_path: Validated video path.
            interval: Frame interval.
            limit: Optional frame limit.
            cancel_check: Optional cancellation callback.

        Returns:
            List of frame dicts.

        Raises:
            AIError: If the video cannot be read.
        """
        frames: list[dict[str, Any]] = []
        cap = open_video(video_path)
        try:
            info = get_video_info(cap)
            fps = info.get("fps", 0.0) or 30.0
            frame_index = 0
            while True:
                if limit is not None and len(frames) >= limit:
                    break
                if cancel_check is not None and cancel_check():
                    logger.info(
                        "Frame extraction cancelled for '%s' after %d frame(s).",
                        video_path.name,
                        len(frames),
                    )
                    break

                ret, frame = cap.read()
                if not ret or frame is None:
                    break

                if frame_index % interval == 0:
                    try:
                        validate_image(frame)
                    except ValidationError as exc:
                        logger.warning(
                            "Skipping invalid frame %d in '%s': %s",
                            frame_index,
                            video_path.name,
                            exc,
                        )
                    else:
                        frames.append(
                            {
                                "frame": frame,
                                "frame_number": frame_index,
                                "timestamp": self._timestamp(frame_index, fps),
                            }
                        )
                frame_index += 1
        finally:
            close_video(cap)
        return frames

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return extraction statistics.

        Returns:
            Dictionary with keys ``interval``, ``limit``, ``use_mock``,
            ``total_extracted``, and ``last_error``.
        """
        return {
            "interval": self._interval,
            "limit": self._limit,
            "use_mock": self._use_mock,
            "total_extracted": self._frames_extracted,
            "last_error": self._last_error,
        }

    def reset(self) -> None:
        """Reset internal counters."""
        self._frames_extracted = 0
        self._last_error = None

    def __repr__(self) -> str:
        return (
            f"FrameExtractor(interval={self._interval}, limit={self._limit}, "
            f"mock={self._use_mock})"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["FrameExtractor"]

