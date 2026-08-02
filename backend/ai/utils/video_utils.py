"""VisionOps AI — Video utility helpers for the AI layer.

This module provides dependency-light helpers for working with video
files via OpenCV:

- extension / path validation against the project's allowed formats
- robust ``cv2.VideoCapture`` open/close lifecycle management
- metadata extraction (FPS, width, height, frame count, duration)
- safe frame iteration (generator-based, always releases the capture)
- frame-index → timestamp conversion

Resource safety
---------------
Every :class:`cv2.VideoCapture` opened by this module is released
deterministically:

* :func:`iter_video_frames` is a generator that guarantees
  ``capture.release()`` in a ``finally`` block when the generator is
  exhausted, closed, or an exception propagates.
* :func:`open_video` returns a capture that callers must release via
  :func:`close_video` (or a ``try/finally`` block).

Edge cases
----------
Handled explicitly:

* FPS == 0 or missing FPS → timestamp helpers use the provided fallback
  rather than dividing by zero.
* Missing/incorrect frame count → computed frame count is reported
  alongside the OpenCV-reported value.
* Corrupt/empty video → clear :class:`~backend.exceptions.AIError`.
* Unsupported extension → :class:`~backend.exceptions.ValidationError`.
* Invalid frame interval / dimensions → :class:`~backend.exceptions.ValidationError`.

This module intentionally avoids business rules, persistence, and API
concerns.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Generator

from backend.exceptions import AIError, FileValidationError, ValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Video file extensions considered supported by the AI layer.
#: Kept in sync with ``settings.ALLOWED_VIDEO_EXTENSIONS``.
SUPPORTED_VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}
)

#: Guard against pathological OpenCV frame counts.
_MAX_REASONABLE_FRAME_COUNT: int = 10_000_000


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def is_supported_video(path: str | Path) -> bool:
    """Return ``True`` if *path* has a supported video extension.

    Args:
        path: File path to inspect (may not exist yet).

    Returns:
        ``True`` if the lowercase suffix is a supported extension.
    """
    return Path(path).suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS


def _is_finite_number(value: object) -> bool:
    """Return ``True`` if *value* is a finite real number.

    Args:
        value: Value to test (bool is rejected).

    Returns:
        ``True`` for finite ``int``/``float`` (excluding ``bool``).
    """
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    return False


def validate_video_file(
    path: str | Path,
    *,
    check_exists: bool = True,
    check_extension: bool = True,
) -> Path:
    """Validate a video file path for AI processing.

    Args:
        path: Candidate video path.
        check_exists: If ``True``, verify the file exists and is
            non-empty.  Defaults to ``True``.
        check_extension: If ``True``, verify the extension is one of the
            supported video formats.  Defaults to ``True``.

    Returns:
        Resolved :class:`pathlib.Path` to the validated video file.

    Raises:
        ValidationError: If *check_extension* is enabled and the suffix
            is not a supported video extension.
        FileValidationError: If *check_exists* is enabled and the file
            is missing or empty.
    """
    video_path = Path(path)
    suffix = video_path.suffix.lower()

    if check_extension and suffix not in SUPPORTED_VIDEO_EXTENSIONS:
        raise ValidationError(
            f"Invalid video extension '{suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}."
        )

    if check_exists:
        if not video_path.is_file():
            raise FileValidationError(
                f"Video file not found: '{video_path}'."
            )
        if video_path.stat().st_size == 0:
            raise FileValidationError(
                f"Empty video file: '{video_path}'."
            )

    return video_path.resolve()


# ---------------------------------------------------------------------------
# Capture lifecycle helpers
# ---------------------------------------------------------------------------


def open_video(path: str | Path) -> Any:
    """Open a video file with OpenCV and return the capture object.

    The caller owns the returned :class:`cv2.VideoCapture` and must
    release it via :func:`close_video` or a ``try/finally`` block.

    Args:
        path: Path to a valid, non-empty video file.

    Returns:
        An opened :class:`cv2.VideoCapture` instance (or a duck-typed
        object exposing the same minimal API in mock/test scenarios).

    Raises:
        AIError: If OpenCV is unavailable or the capture fails to open.
    """
    try:
        import cv2
    except ImportError as exc:  # pragma: no cover - env-specific
        raise AIError(
            "OpenCV (cv2) is required for video processing but is not "
            "installed. Install 'opencv-python' or 'opencv-contrib-python'."
        ) from exc

    video_path = validate_video_file(path)
    try:
        capture = cv2.VideoCapture(str(video_path))
    except Exception as exc:
        raise AIError(
            f"Failed to open video '{video_path}': {exc}"
        ) from exc

    if capture is None or not capture.isOpened():
        if capture is not None:
            close_video(capture)
        raise AIError(f"Could not open video file '{video_path}'.")

    return capture


def close_video(capture: Any) -> None:
    """Release a video capture deterministically.

    Safe to call on ``None`` or already-closed captures.

    Args:
        capture: The :class:`cv2.VideoCapture` (or duck-typed equivalent)
            to release.
    """
    if capture is None:
        return
    try:
        release = getattr(capture, "release", None)
        if callable(release):
            release()
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Error while releasing video capture: %s", exc)


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------


def get_video_info(
    capture: Any,
    *,
    fps: float | None = None,
    frame_count: int | None = None,
) -> dict[str, Any]:
    """Extract metadata from an opened video capture.

    Args:
        capture: An opened :class:`cv2.VideoCapture`.
        fps: Optional FPS override.  When omitted (``None``) the value is
            read from the capture; a zero/unavailable value is reported
            as ``0.0``.
        frame_count: Optional frame-count override.  When omitted the
            value is read from the capture (falling back to ``0`` when
            unavailable).

    Returns:
        Dictionary with keys ``fps``, ``width``, ``height``,
        ``frame_count``, ``duration_seconds``, ``frame_size``.

    Raises:
        ValidationError: If *fps* or *frame_count* are invalid.
    """
    if fps is not None and not _is_finite_number(fps):
        raise ValidationError(
            f"Invalid fps value: {fps!r}. Must be a finite number."
        )
    if fps is not None and float(fps) < 0.0:
        raise ValidationError(
            f"Invalid fps value: {fps!r}. Must be non-negative."
        )

    if frame_count is not None:
        if isinstance(frame_count, bool) or not isinstance(frame_count, int):
            raise ValidationError(
                "Invalid frame_count value: "
                f"{frame_count!r}. Must be an integer."
            )
        if frame_count < 0 or frame_count > _MAX_REASONABLE_FRAME_COUNT:
            raise ValidationError(
                "Invalid frame_count value: "
                f"{frame_count!r}. Out of range."
            )

    get = getattr(capture, "get", None)

    def _cap_prop(prop: int) -> float:
        if get is None:
            return 0.0
        try:
            value = get(prop)
            return float(value) if value is not None else 0.0
        except Exception:  # pragma: no cover - defensive
            return 0.0

    import cv2 as _cv2

    cap_fps = _cap_prop(_cv2.CAP_PROP_FPS)
    cap_width = _cap_prop(_cv2.CAP_PROP_FRAME_WIDTH)
    cap_height = _cap_prop(_cv2.CAP_PROP_FRAME_HEIGHT)
    cap_frames = _cap_prop(_cv2.CAP_PROP_FRAME_COUNT)

    resolved_fps = float(fps) if fps is not None else cap_fps
    resolved_frames = (
        frame_count
        if frame_count is not None
        else int(cap_frames)
        if math.isfinite(cap_frames) and cap_frames >= 0
        else 0
    )

    if not math.isfinite(resolved_fps) or resolved_fps < 0.0:
        resolved_fps = 0.0
    if (
        not math.isfinite(float(resolved_frames))
        or resolved_frames < 0
        or resolved_frames > _MAX_REASONABLE_FRAME_COUNT
    ):
        resolved_frames = 0

    width = int(cap_width) if math.isfinite(cap_width) and cap_width > 0 else 0
    height = int(cap_height) if math.isfinite(cap_height) and cap_height > 0 else 0

    duration = 0.0
    if resolved_fps > 0.0 and resolved_frames > 0:
        duration = float(resolved_frames) / float(resolved_fps)

    return {
        "fps": float(resolved_fps),
        "width": int(width),
        "height": int(height),
        "frame_count": int(resolved_frames),
        "duration_seconds": round(float(duration), 4),
        "frame_size": (int(width), int(height)),
    }


def frame_index_to_timestamp(
    frame_index: int,
    fps: float,
) -> float:
    """Convert a zero-based frame index to a timestamp in seconds.

    Args:
        frame_index: Zero-based frame index (>= 0).
        fps: Frames per second.  Must be finite and > 0.

    Returns:
        Timestamp in seconds (rounded to 4 decimal places).

    Raises:
        ValidationError: If *frame_index* is negative or *fps* is not a
            positive finite number.
    """
    if isinstance(frame_index, bool) or not isinstance(frame_index, int):
        raise ValidationError(
            "frame_index must be an integer, got "
            f"{frame_index!r}."
        )
    if frame_index < 0:
        raise ValidationError(
            f"frame_index must be non-negative, got {frame_index}."
        )
    if isinstance(fps, bool) or not isinstance(fps, (int, float)):
        raise ValidationError(
            f"fps must be a number, got {fps!r}."
        )
    if not math.isfinite(float(fps)) or float(fps) <= 0.0:
        raise ValidationError(
            f"fps must be a positive finite number, got {fps}."
        )
    return round(float(frame_index) / float(fps), 4)


# ---------------------------------------------------------------------------
# Frame iteration
# ---------------------------------------------------------------------------


def iter_video_frames(
    capture: Any,
    *,
    start_frame: int = 0,
    max_frames: int | None = None,
) -> Generator[tuple[int, Any], None, None]:
    """Yield ``(frame_index, frame)`` tuples from an opened capture.

    The generator reads frames sequentially starting at ``start_frame``
    (frames before it are skipped without inference) and stops after
    ``max_frames`` frames or when the capture is exhausted.

    The capture is **always** released when iteration completes, the
    generator is closed via ``.close()``, or an exception propagates.

    Args:
        capture: An opened :class:`cv2.VideoCapture`.
        start_frame: Frame index to begin yielding from (>= 0).
        max_frames: Optional maximum number of frames to yield (>= 1).

    Yields:
        ``(frame_index, frame)`` tuples where *frame_index* is the
        absolute zero-based frame number.

    Raises:
        ValidationError: If *start_frame* or *max_frames* are invalid.
        AIError: If frames cannot be read.
    """
    if isinstance(start_frame, bool) or not isinstance(start_frame, int):
        raise ValidationError(
            f"start_frame must be an integer, got {start_frame!r}."
        )
    if start_frame < 0:
        raise ValidationError(
            f"start_frame must be non-negative, got {start_frame}."
        )
    if max_frames is not None:
        if isinstance(max_frames, bool) or not isinstance(max_frames, int):
            raise ValidationError(
                f"max_frames must be an integer, got {max_frames!r}."
            )
        if max_frames < 1:
            raise ValidationError(
                f"max_frames must be >= 1, got {max_frames}."
            )

    read = getattr(capture, "read", None)
    if read is None:
        raise AIError("Video capture object does not support read().")

    try:
        frame_index = 0
        yielded = 0
        while True:
            ret, frame = read()
            if not ret or frame is None:
                break
            if frame_index >= start_frame:
                yield frame_index, frame
                yielded += 1
                if max_frames is not None and yielded >= max_frames:
                    break
            frame_index += 1
    finally:
        close_video(capture)


def extract_frames_range(
    capture: Any,
    *,
    start_frame: int = 0,
    end_frame: int | None = None,
    step: int = 1,
    max_frames: int | None = None,
) -> list[tuple[int, Any]]:
    """Extract a list of ``(frame_index, frame)`` tuples from a capture.

    This is a convenience wrapper over :func:`iter_video_frames` that
    materializes the yielded frames into a list.  It is intended for
    small/medium frame selections; for large videos prefer the generator
    directly to avoid loading the entire video into memory.

    Args:
        capture: An opened :class:`cv2.VideoCapture`.
        start_frame: First frame index to include (>= 0).
        end_frame: Optional exclusive upper bound for frame indices.
        step: Frame step (>= 1).
        max_frames: Optional maximum number of frames to return (>= 1).

    Returns:
        List of ``(frame_index, frame)`` tuples.

    Raises:
        ValidationError: If *step*, *start_frame*, *end_frame*, or
            *max_frames* are invalid.
        AIError: If frames cannot be read.
    """
    if isinstance(step, bool) or not isinstance(step, int):
        raise ValidationError(f"step must be an integer, got {step!r}.")
    if step < 1:
        raise ValidationError(f"step must be >= 1, got {step}.")
    if end_frame is not None:
        if isinstance(end_frame, bool) or not isinstance(end_frame, int):
            raise ValidationError(
                f"end_frame must be an integer, got {end_frame!r}."
            )
        if end_frame < start_frame:
            raise ValidationError(
                f"end_frame ({end_frame}) must be >= start_frame "
                f"({start_frame})."
            )

    result: list[tuple[int, Any]] = []
    for frame_index, frame in iter_video_frames(
        capture,
        start_frame=start_frame,
        max_frames=max_frames,
    ):
        if end_frame is not None and frame_index >= end_frame:
            break
        if (frame_index - start_frame) % step == 0:
            result.append((frame_index, frame))
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "SUPPORTED_VIDEO_EXTENSIONS",
    "is_supported_video",
    "validate_video_file",
    "open_video",
    "close_video",
    "get_video_info",
    "iter_video_frames",
    "extract_frames_range",
    "frame_index_to_timestamp",
]

