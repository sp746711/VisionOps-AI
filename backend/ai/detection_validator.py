"""VisionOps AI — Detection output validator.

Validates AI-inference output for **structural quality only**.  This
module does *not* implement spoilage risk, domain category, or other
business rules — those belong to the business/services layers.

Responsibilities
----------------
* Reject malformed detection dicts (missing required fields).
* Reject NaN / ±Infinity confidence scores.
* Reject non-numeric or negative bounding boxes and degenerate boxes.
* Reject invalid class values (non-string, empty, non-finite).
* Optionally clamp bounding boxes to frame dimensions when provided.
* Batch validation with per-detection boolean results.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from typing import Any

from backend.exceptions import ValidationError
from backend.schemas.common import DetectionClass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS: frozenset[str] = frozenset({"class_name", "confidence", "bbox"})
_BBOX_SIZE: int = 4
_MIN_BOX_WIDTH: float = 1e-6
_MIN_BOX_HEIGHT: float = 1e-6

#: Classes recognised by the project.  A dict may also carry additional
#: model-specific names; structural validation only requires a valid
#: non-empty string unless ``strict_classes=True``.
_KNOWN_CLASSES: frozenset[str] = frozenset(c.value for c in DetectionClass)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_finite_number(value: Any) -> bool:
    """Return ``True`` if *value* is a finite (non-bool) real number.

    Args:
        value: Value to inspect.

    Returns:
        ``True`` for finite ``int``/``float`` (excluding ``bool``).
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _validate_confidence(confidence: Any, *, idx: int) -> float:
    """Validate a raw confidence score.

    Args:
        confidence: Raw value.
        idx: Detection index (for error messages).

    Returns:
        The finite confidence value.

    Raises:
        ValidationError: If the confidence is non-numeric, non-finite, or
            out of the ``[0.0, 1.0]`` range.
    """
    if not _is_finite_number(confidence):
        raise ValidationError(
            f"Detection at index {idx}: confidence must be a finite "
            f"number, got {confidence!r}."
        )
    value = float(confidence)
    if value < 0.0 or value > 1.0:
        raise ValidationError(
            f"Detection at index {idx}: confidence must be in "
            f"[0.0, 1.0], got {value}."
        )
    return value


def _validate_bbox(
    bbox: Any,
    *,
    idx: int,
    frame_size: tuple[int, int] | None = None,
    clamp_coords: bool = False,
    strict_classes: bool = False,
) -> list[float] | None:
    """Validate a bounding box representation.

    Accepts a positional ``[x, y, w, h]`` sequence of finite non-negative
    numbers.  Returns the normalized list, or ``None`` when the box is
    fundamentally malformed (used by the lenient :class:`DetectionValidator`
    public API).

    Args:
        bbox: Raw bounding-box value.
        idx: Detection index (for error messages).
        frame_size: Optional ``(width, height)`` frame dimensions used to
            validate frame boundaries.
        clamp_coords: When ``True``, coordinates are clamped to the frame
            (only used when *frame_size* is provided).
        strict_classes: Reserved for future validation strictness.

    Returns:
        List of four finite non-negative floats, or ``None`` if the box
        is malformed.

    Raises:
        ValidationError: For clearly invalid boxes when *clamp_coords* or
            *frame_size* produce an impossible/negative remaining box.
    """
    del strict_classes  # reserved, no structural effect today

    if not isinstance(bbox, (list, tuple)):
        return None
    if len(bbox) != _BBOX_SIZE:
        return None

    values: list[float] = []
    for value in bbox:
        if not _is_finite_number(value):
            return None
        values.append(float(value))

    x, y, width, height = values
    if width < 0.0 or height < 0.0 or x < 0.0 or y < 0.0:
        return None

    if width < _MIN_BOX_WIDTH or height < _MIN_BOX_HEIGHT:
        logger.debug(
            "Detection at index %d skipped: degenerate box %s.",
            idx,
            values,
        )
        return None

    if frame_size is not None:
        frame_w, frame_h = frame_size
        if frame_w <= 0 or frame_h <= 0:
            raise ValidationError(
                f"Detection at index {idx}: invalid frame size {frame_size}."
            )

        if not clamp_coords:
            # Coordinates must fall within the frame.
            if x + width > frame_w + 1e-6 or y + height > frame_h + 1e-6:
                return None
        else:
            # Clamp origin and shrink oversized boxes to the frame.
            clamped_x = min(max(x, 0.0), float(frame_w))
            clamped_y = min(max(y, 0.0), float(frame_h))
            max_w = max(float(frame_w) - clamped_x, 0.0)
            max_h = max(float(frame_h) - clamped_y, 0.0)
            width = min(width, max_w)
            height = min(height, max_h)
            if width < _MIN_BOX_WIDTH or height < _MIN_BOX_HEIGHT:
                return None
            values = [clamped_x, clamped_y, width, height]

    return values


def _validate_class_name(class_name: Any, *, idx: int) -> str:
    """Validate a raw class name.

    Args:
        class_name: Raw class value.
        idx: Detection index (for error messages).

    Returns:
        The normalized (lowercased, stripped) class string.

    Raises:
        ValidationError: If the class name is not a non-empty string.
    """
    if not isinstance(class_name, str) or not class_name.strip():
        raise ValidationError(
            f"Detection at index {idx}: class_name must be a non-empty "
            f"string, got {class_name!r}."
        )
    return class_name.strip().lower()


# ---------------------------------------------------------------------------
# DetectionValidator
# ---------------------------------------------------------------------------


class DetectionValidator:
    """Structural validator for AI detection output.

    Validates the *shape and numeric integrity* of detection dicts in the
    project contract::

        {"class_name": str, "confidence": float, "bbox": [x, y, w, h]}

    The public ``validate``/``validate_batch`` API is lenient-by-design:
    malformed entries are rejected (return ``False``) rather than raising,
    matching the existing service-layer behavior of skipping invalid rows.

    For callers that need **strict** validation, use
    :meth:`validate_strict` which raises
    :class:`~backend.exceptions.ValidationError`.

    Args:
        require_known_class: When ``True``, ``class_name`` must be one of
            the project's :class:`~backend.schemas.common.DetectionClass`
            values.  Defaults to ``False`` (structural validation only).
        frame_size: Optional ``(width, height)`` frame dimensions used to
            reject boxes that leave the frame.
        clamp_coords: When ``True`` (and *frame_size* is set), boxes are
            clamped to the frame instead of being rejected.
        min_confidence: Optional minimum confidence threshold for
            acceptance (independent of business rules; purely structural).
    """

    def __init__(
        self,
        *,
        require_known_class: bool = False,
        frame_size: tuple[int, int] | None = None,
        clamp_coords: bool = False,
        min_confidence: float | None = None,
    ) -> None:
        """Initialise the validator."""
        if frame_size is not None:
            if (
                not isinstance(frame_size, (tuple, list))
                or len(frame_size) != 2
            ):
                raise ValidationError(
                    "frame_size must be a (width, height) tuple/list, got "
                    f"{frame_size!r}."
                )
            width, height = frame_size
            if (
                isinstance(width, bool)
                or isinstance(height, bool)
                or not isinstance(width, (int, float))
                or not isinstance(height, (int, float))
                or width <= 0
                or height <= 0
            ):
                raise ValidationError(
                    f"frame_size must contain positive numbers, got {frame_size!r}."
                )

        if min_confidence is not None and not _is_finite_number(min_confidence):
            raise ValidationError(
                f"min_confidence must be a finite number, got {min_confidence!r}."
            )

        self._require_known_class = bool(require_known_class)
        self._frame_size = (
            (int(frame_size[0]), int(frame_size[1]))
            if frame_size is not None
            else None
        )
        self._clamp_coords = bool(clamp_coords)
        self._min_confidence = (
            float(min_confidence) if min_confidence is not None else None
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, detection: dict[str, Any]) -> bool:
        """Validate a single detection dict (lenient).

        Args:
            detection: Raw detection dict.

        Returns:
            ``True`` if the detection is structurally valid, ``False``
            otherwise (no exception raised).
        """
        try:
            self._validate_impl(detection)
            return True
        except ValidationError:
            return False

    def validate_batch(self, detections: Sequence[dict[str, Any]]) -> list[bool]:
        """Validate a batch of detection dicts (lenient).

        Args:
            detections: Sequence of raw detection dicts.

        Returns:
            List of booleans, one per input detection.
        """
        if not isinstance(detections, (list, tuple)):
            raise ValidationError(
                "detections must be a list/tuple, got "
                f"{type(detections).__name__}."
            )
        return [self.validate(det) for det in detections]

    def validate_strict(self, detection: dict[str, Any]) -> dict[str, Any]:
        """Validate a single detection dict (strict).

        Args:
            detection: Raw detection dict.

        Returns:
            The normalized detection dict with the ``bbox`` as a
            four-element float list.

        Raises:
            ValidationError: If the detection is malformed.
        """
        return self._validate_impl(detection)

    def validate_batch_strict(
        self, detections: Sequence[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Validate a batch of detection dicts (strict).

        Args:
            detections: Sequence of raw detection dicts.

        Returns:
            List of normalized detection dicts.

        Raises:
            ValidationError: If any detection is malformed.
        """
        if not isinstance(detections, (list, tuple)):
            raise ValidationError(
                "detections must be a list/tuple, got "
                f"{type(detections).__name__}."
            )
        return [self._validate_impl(det) for det in detections]

    # ------------------------------------------------------------------
    # Implementation
    # ------------------------------------------------------------------

    def _validate_impl(self, detection: dict[str, Any]) -> dict[str, Any]:
        """Core validation logic shared by lenient and strict paths.

        Args:
            detection: Raw detection dict.

        Returns:
            The normalized detection dict.

        Raises:
            ValidationError: If validation fails.
        """
        if not isinstance(detection, dict):
            raise ValidationError(
                f"Detection must be a dict, got {type(detection).__name__}."
            )

        missing = _REQUIRED_FIELDS - set(detection)
        if missing:
            raise ValidationError(
                "Detection missing required field(s): "
                f"{', '.join(sorted(missing))}."
            )

        class_name = _validate_class_name(detection["class_name"], idx=-1)
        confidence = _validate_confidence(detection["confidence"], idx=-1)

        if self._require_known_class and class_name not in _KNOWN_CLASSES:
            raise ValidationError(
                f"Unknown class_name '{class_name}'. Known classes: "
                f"{', '.join(sorted(_KNOWN_CLASSES))}."
            )

        if self._min_confidence is not None and confidence < self._min_confidence:
            raise ValidationError(
                f"Detection confidence {confidence} is below the minimum "
                f"threshold {self._min_confidence}."
            )

        bbox = _validate_bbox(
            detection["bbox"],
            idx=-1,
            frame_size=self._frame_size,
            clamp_coords=self._clamp_coords,
        )
        if bbox is None:
            # Force a ValidationError with a consistent message by relying
            # on the strict path re-checking the raw box format.
            raise ValidationError(
                "Detection has an invalid bbox: must be a [x, y, width, "
                f"height] sequence of finite non-negative numbers, got "
                f"{detection['bbox']!r}."
            )

        return {
            "class_name": class_name,
            "confidence": round(confidence, 6),
            "bbox": bbox,
            "track_id": detection.get("track_id"),
        }

    def __repr__(self) -> str:
        return (
            f"DetectionValidator(require_known_class="
            f"{self._require_known_class}, frame_size={self._frame_size}, "
            f"clamp_coords={self._clamp_coords}, "
            f"min_confidence={self._min_confidence})"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["DetectionValidator"]

