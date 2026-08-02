"""VisionOps AI — Multi-object tracking adapter (ByteTrack-compatible).

This module provides the tracking adapter used by the AI pipeline.  It
turns per-frame detections into track-associated detections with stable
track IDs.

Two modes are supported:

* **Mock mode** (``use_mock=True``) — intended for unit tests and CI.  No
  tracking backend is required.  Detections are passed through with
  ``track_id=None`` and **no fabricated track IDs** are created.
* **Real mode** (``use_mock=False``) — requires the optional
  ``bytetrack``/``ultralytics`` tracking stack.  When the backend is
  unavailable, :meth:`update` raises a clear
  :class:`~backend.exceptions.AIError` **only** when tracking is actually
  requested.

State isolation
---------------
Each :class:`ByteTrackTracker` owns its state (no module-level mutable
state).  Call :meth:`reset` between independent videos to guarantee that
tracking state never leaks from one video to another.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.core.config import settings
from backend.exceptions import AIError
from backend.exceptions import ValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TRACK_ID_PREFIX: str = "track_"
_TRACK_FALLBACK_CLASSES: frozenset[str] = frozenset(
    {"person", "forklift", "truck", "pallet"}
)


def _is_finite_number(value: Any) -> bool:
    """Return ``True`` for finite real numbers (excluding bool)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    import math

    return math.isfinite(float(value))


def _validate_bbox(bbox: Any) -> list[float] | None:
    """Validate a ``[x, y, w, h]`` detection box; return float list or None."""
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return None
    values: list[float] = []
    for value in bbox:
        if not _is_finite_number(value):
            return None
        values.append(float(value))
    x, y, width, height = values
    if x < 0.0 or y < 0.0 or width <= 0.0 or height <= 0.0:
        return None
    return values


# ---------------------------------------------------------------------------
# ByteTrackTracker
# ---------------------------------------------------------------------------


class ByteTrackTracker:
    """Per-instance multi-object tracker adapter.

    Args:
        enabled: Override for tracking enablement.  When ``None``, the
            configured ``settings.BYTETRACK_ENABLED`` is used.
        match_threshold: Association threshold in ``[0.0, 1.0]``.  When
            ``None``, ``settings.BYTETRACK_MATCH_THRESHOLD`` is used.
        track_buffer: Maximum frames a lost track is kept alive.  When
            ``None``, ``settings.BYTETRACK_TRACK_BUFFER`` is used.
        use_mock: Test-only flag.  When ``True``, no tracking backend is
            required and detections pass through with ``track_id=None``.
            Defaults to ``False``.
    """

    def __init__(
        self,
        enabled: bool | None = None,
        match_threshold: float | None = None,
        track_buffer: int | None = None,
        use_mock: bool = False,
    ) -> None:
        """Initialise the tracker (no backend is loaded here)."""
        self._enabled: bool = (
            enabled if enabled is not None else settings.BYTETRACK_ENABLED
        )
        self._match_threshold: float = (
            match_threshold
            if match_threshold is not None
            else settings.BYTETRACK_MATCH_THRESHOLD
        )
        self._track_buffer: int = (
            track_buffer if track_buffer is not None else settings.BYTETRACK_TRACK_BUFFER
        )
        self._use_mock: bool = bool(use_mock)

        self._validate_config()

        # Backend instance (created lazily in real mode).
        self._backend: Any | None = None
        self._frame_count: int = 0

    # ------------------------------------------------------------------
    # Configuration validation
    # ------------------------------------------------------------------

    def _validate_config(self) -> None:
        """Validate tracker configuration.

        Raises:
            ValidationError: If any configuration value is invalid.
        """
        if not _is_finite_number(self._match_threshold):
            raise ValidationError(
                f"match_threshold must be a finite number, got "
                f"{self._match_threshold!r}."
            )
        if not (0.0 <= float(self._match_threshold) <= 1.0):
            raise ValidationError(
                f"match_threshold must be in [0.0, 1.0], got "
                f"{self._match_threshold}."
            )

        if (
            isinstance(self._track_buffer, bool)
            or not isinstance(self._track_buffer, int)
            or self._track_buffer < 1
        ):
            raise ValidationError(
                "track_buffer must be a positive integer, got "
                f"{self._track_buffer!r}."
            )

    # ------------------------------------------------------------------
    # Tracking API
    # ------------------------------------------------------------------

    def update(self, detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Update tracking state with detections for the current frame.

        Args:
            detections: List of raw detection dicts in the project
                contract (``class_name``, ``confidence``, ``bbox``).  An
                empty list clears associations for the frame and returns
                an empty list.

        Returns:
            List of detection dicts enriched with a ``track_id`` value
            (string like ``"track_1"`` in real mode; ``None`` in mock
            mode).  The input dicts are not mutated.

        Raises:
            ValidationError: If *detections* is not a list.
            AIError: If tracking is requested in real mode but the
                tracking backend is unavailable.
        """
        if not isinstance(detections, list):
            raise ValidationError(
                f"detections must be a list, got {type(detections).__name__}."
            )

        if self._use_mock:
            if detections:
                logger.debug(
                    "ByteTrack mock mode — passing through %d detection(s) "
                    "without track IDs.",
                    len(detections),
                )
            return [dict(det) for det in detections]

        if not self._enabled:
            return [dict(det) for det in detections]

        if not detections:
            self._advance_frame()
            return []

        backend = self._ensure_backend()
        try:
            tracks = backend.update(detections)
        except Exception as exc:
            raise AIError(f"ByteTrack tracking update failed: {exc}") from exc

        self._advance_frame()
        return tracks

    def reset(self) -> "ByteTrackTracker":
        """Reset all tracking state.

        Must be called between independent videos so track IDs never leak
        across videos.  In mock mode this simply clears the frame counter.

        Returns:
            ``self`` to allow method chaining.
        """
        self._frame_count = 0
        backend = self._backend
        if backend is not None:
            try:
                reset = getattr(backend, "reset", None)
                if callable(reset):
                    reset()
            except Exception as exc:
                logger.warning("ByteTrack backend reset failed: %s", exc)
            self._backend = None
        logger.debug("ByteTrackTracker state reset.")
        return self

    # ------------------------------------------------------------------
    # Status / info
    # ------------------------------------------------------------------

    def is_enabled(self) -> bool:
        """Return ``True`` if tracking is enabled for this instance."""
        return self._enabled

    def get_tracker_info(self) -> dict[str, Any]:
        """Return metadata about the tracker.

        Returns:
            Dictionary with keys ``enabled``, ``match_threshold``,
            ``track_buffer``, ``use_mock``, ``frame_count``, and
            ``backend_configured``.
        """
        return {
            "enabled": self._enabled,
            "match_threshold": self._match_threshold,
            "track_buffer": self._track_buffer,
            "use_mock": self._use_mock,
            "frame_count": self._frame_count,
            "backend_configured": self._backend is not None,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _advance_frame(self) -> None:
        """Increment the internal frame counter."""
        self._frame_count += 1

    def _ensure_backend(self) -> Any:
        """Lazily create the real tracking backend.

        Returns:
            A tracker backend object exposing ``update(detections)`` and
            optional ``reset()``.

        Raises:
            AIError: If the optional ``bytetrack``/``boxmot`` tracking
                stack is unavailable.
        """
        if self._backend is not None:
            return self._backend

        # Try common ByteTrack-compatible backends.  Order matters:
        #  1. boxmot (modern, pip installable ByteTrack variant)
        #  2. lap/byte_tracker (classic ByteTrack)
        errors: list[str] = []
        try:
            from boxmot import BYTETracker as _BoxmotBYTETracker  # type: ignore

            self._backend = _BoxmotBYTETracker(
                track_buffer=self._track_buffer,
                match_threshold=self._match_threshold,
            )
            logger.info(
                "ByteTrack backend initialised (boxmot, buffer=%d, "
                "threshold=%.2f).",
                self._track_buffer,
                self._match_threshold,
            )
            return self._backend
        except ImportError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(str(exc))

        try:
            from byte_tracker import ByteTrack as _ClassicByteTrack  # type: ignore

            self._backend = _ClassicByteTrack()
            logger.info(
                "ByteTrack backend initialised (byte_tracker)."
            )
            return self._backend
        except ImportError as exc:
            errors.append(str(exc))
        except Exception as exc:
            errors.append(str(exc))

        raise AIError(
            "ByteTrack tracking requires an optional dependency that is "
            "not installed. Install 'boxmot' (recommended) or 'bytetrack' "
            "to enable multi-object tracking. "
            f"Backend import errors: {'; '.join(errors)}"
        )

    def __repr__(self) -> str:
        return (
            f"ByteTrackTracker(enabled={self._enabled}, "
            f"match_threshold={self._match_threshold}, "
            f"track_buffer={self._track_buffer}, mock={self._use_mock})"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["ByteTrackTracker"]

