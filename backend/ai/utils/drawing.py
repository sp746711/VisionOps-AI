"""VisionOps AI — Drawing / annotation helpers for the AI layer.

Provides visualization helpers for annotating frames with detection
results:

- bounding-box drawing with clamped, validated coordinates
- class/label text with confidence and optional track-ID overlays
- per-class color palettes derived from the project's detection classes
- batch annotation over a list of detections

Non-mutating by default
-----------------------
By default all functions draw onto a **copy** of the source frame so the
caller's original image is never mutated.  Pass ``inplace=True`` (where
supported) to draw directly onto the source frame.

Input safety
------------
* Bounding boxes are validated for finite, non-negative, positive-size
  coordinates.
* Coordinates are **clamped** to the frame boundaries so partially
  out-of-frame boxes are drawn safely.
* Fundamentally malformed boxes (NaN, negative dims, non-numeric) are
  rejected with :class:`~backend.exceptions.ValidationError` rather than
  silently drawn.

This module contains **no business logic**.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Mapping, Sequence

from backend.exceptions import AIError, ValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default line thickness for bounding boxes.
_DEFAULT_THICKNESS: int = 2

#: Default font scale for label text.
_DEFAULT_FONT_SCALE: float = 0.5

#: Default label background padding in pixels.
_DEFAULT_PADDING: int = 2


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _as_finite_float(value: object, *, name: str) -> float:
    """Convert *value* to a finite float, rejecting non-numeric values.

    Args:
        value: Value to convert.
        name: Field name for error messages.

    Returns:
        Finite float.

    Raises:
        ValidationError: If the value is not a finite real number.
    """
    if isinstance(value, bool):
        raise ValidationError(f"{name} must be a number, got bool.")
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            f"{name} must be a number, got {value!r}."
        ) from exc
    if not math.isfinite(number):
        raise ValidationError(
            f"{name} must be finite, got {value!r}."
        )
    return number


def _validate_bbox(bbox: Sequence[float]) -> tuple[float, float, float, float]:
    """Validate a ``[x, y, w, h]`` bounding box.

    Args:
        bbox: Sequence of exactly four numeric values.

    Returns:
        ``(x, y, width, height)`` as finite floats.

    Raises:
        ValidationError: If the box is malformed (wrong length, negative
            or non-finite coordinates, non-positive dimensions).
    """
    if not isinstance(bbox, (list, tuple)):
        raise ValidationError(
            f"bbox must be a list/tuple of 4 numbers, got {type(bbox).__name__}."
        )
    if len(bbox) != 4:
        raise ValidationError(
            f"bbox must contain exactly 4 values, got {len(bbox)}."
        )

    x = _as_finite_float(bbox[0], name="bbox[0] (x)")
    y = _as_finite_float(bbox[1], name="bbox[1] (y)")
    w = _as_finite_float(bbox[2], name="bbox[2] (width)")
    h = _as_finite_float(bbox[3], name="bbox[3] (height)")

    if x < 0.0 or y < 0.0:
        raise ValidationError(
            f"bbox origin must be non-negative, got ({x}, {y})."
        )
    if w <= 0.0 or h <= 0.0:
        raise ValidationError(
            f"bbox dimensions must be positive, got ({w}, {h})."
        )

    return x, y, w, h


def _clamp_bbox(
    x: float,
    y: float,
    w: float,
    h: float,
    frame_width: int,
    frame_height: int,
) -> tuple[int, int, int, int]:
    """Clamp a box to integer coordinates within the frame boundaries.

    Args:
        x: Box left coordinate.
        y: Box top coordinate.
        w: Box width.
        h: Box height.
        frame_width: Frame width in pixels.
        frame_height: Frame height in pixels.

    Returns:
        ``(x1, y1, x2, y2)`` integer pixel coordinates fully clamped to
        the frame.  If the box lies entirely outside the frame a
        degenerate zero-area box is returned.
    """
    x1 = max(int(math.floor(x)), 0)
    y1 = max(int(math.floor(y)), 0)
    x2 = min(int(math.ceil(x + w)), frame_width)
    y2 = min(int(math.ceil(y + h)), frame_height)
    return x1, y1, x2, y2


def _image_frame(image: Any) -> tuple[int, int]:
    """Return ``(width, height)`` for an image, validating its shape.

    Args:
        image: Image array.

    Returns:
        ``(width, height)`` tuple.

    Raises:
        ValidationError: If the image shape is invalid.
    """
    shape = getattr(image, "shape", None)
    if shape is None or len(shape) < 2:
        raise ValidationError(
            "Image must expose a 'shape' with at least 2 dimensions, "
            f"got {type(image).__name__}."
        )
    height = int(shape[0])
    width = int(shape[1])
    if height <= 0 or width <= 0:
        raise ValidationError(
            f"Image dimensions must be positive, got ({height}, {width})."
        )
    return width, height


def get_class_color(class_name: str) -> tuple[int, int, int]:
    """Return a stable BGR color for a detection class name.

    Uses a deterministic hash so the same class always maps to the same
    color across calls.

    Args:
        class_name: Detection class name (string).

    Returns:
        A ``(B, G, R)`` tuple in ``[0, 255]``.
    """
    # Simple deterministic palette of visually distinct colors (BGR).
    palette: tuple[tuple[int, int, int], ...] = (
        (255, 0, 0),    # red
        (0, 255, 0),    # green
        (0, 0, 255),    # blue
        (0, 255, 255),  # yellow
        (255, 0, 255),  # magenta
        (255, 255, 0),  # cyan
        (0, 165, 255),  # orange
        (128, 0, 128),  # purple
        (0, 255, 128),  # light green
        (255, 128, 0),  # teal-ish
    )
    if not class_name:
        return palette[0]
    index = abs(hash(class_name)) % len(palette)
    return palette[index]


# ---------------------------------------------------------------------------
# Public drawing helpers
# ---------------------------------------------------------------------------


def draw_bounding_box(
    image: Any,
    bbox: Sequence[float],
    *,
    color: tuple[int, int, int] = (255, 0, 0),
    thickness: int = _DEFAULT_THICKNESS,
    inplace: bool = False,
) -> Any:
    """Draw a single bounding box rectangle onto an image.

    Args:
        image: Image array (BGR).
        bbox: ``[x, y, width, height]`` sequence.
        color: ``(B, G, R)`` rectangle color.
        thickness: Line thickness in pixels (>= 1).
        inplace: If ``True``, draw onto the source image; otherwise a
            copy is returned and the source is left unchanged.

    Returns:
        The annotated image (the source if *inplace*, else a copy).

    Raises:
        ValidationError: If the bbox or color is invalid.
        AIError: If OpenCV is unavailable.
    """
    x, y, w, h = _validate_bbox(bbox)
    width, height = _image_frame(image)
    x1, y1, x2, y2 = _clamp_bbox(x, y, w, h, width, height)

    if len(color) != 3 or any(not isinstance(c, int) for c in color):
        raise ValidationError(f"color must be a 3-tuple of ints, got {color!r}.")
    if any(c < 0 or c > 255 for c in color):
        raise ValidationError(f"color channels must be in [0, 255], got {color!r}.")
    if isinstance(thickness, bool) or not isinstance(thickness, int):
        raise ValidationError(f"thickness must be an int, got {thickness!r}.")
    if thickness < 1:
        raise ValidationError(f"thickness must be >= 1, got {thickness}.")

    # A fully out-of-frame box produces a degenerate rectangle; nothing
    # to draw.
    if x2 <= x1 or y2 <= y1:
        return image if inplace else image.copy()

    try:
        import cv2
    except ImportError as exc:
        raise AIError(
            "OpenCV (cv2) is required for drawing but is not installed."
        ) from exc

    target = image if inplace else image.copy()
    cv2.rectangle(target, (x1, y1), (x2, y2), color, thickness)
    return target


def draw_label(
    image: Any,
    text: str,
    position: tuple[int, int],
    *,
    color: tuple[int, int, int] = (255, 0, 0),
    font_scale: float = _DEFAULT_FONT_SCALE,
    thickness: int = _DEFAULT_THICKNESS,
    padding: int = _DEFAULT_PADDING,
    background_color: tuple[int, int, int] | None = None,
    inplace: bool = False,
) -> Any:
    """Draw a text label with an optional filled background.

    Args:
        image: Image array (BGR).
        text: Label text (non-empty string).
        position: ``(x, y)`` bottom-left anchor of the text.
        color: ``(B, G, R)`` text color.
        font_scale: Font scale factor (> 0).
        thickness: Text thickness in pixels (>= 1).
        padding: Background padding in pixels (>= 0).
        background_color: Optional ``(B, G, R)`` filled background.  If
            ``None``, the text is drawn without a background box.
        inplace: If ``True``, draw onto the source image.

    Returns:
        The annotated image.

    Raises:
        ValidationError: If text or numeric parameters are invalid.
        AIError: If OpenCV is unavailable.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValidationError("text must be a non-empty string.")
    if len(position) != 2:
        raise ValidationError(
            f"position must contain 2 values, got {len(position)}."
        )
    pos_x = _as_finite_float(position[0], name="position[0]")
    pos_y = _as_finite_float(position[1], name="position[1]")
    if pos_x < 0 or pos_y < 0:
        raise ValidationError(
            f"position must be non-negative, got ({pos_x}, {pos_y})."
        )
    if len(color) != 3 or any(not isinstance(c, int) for c in color):
        raise ValidationError(f"color must be a 3-tuple of ints, got {color!r}.")
    if any(c < 0 or c > 255 for c in color):
        raise ValidationError(f"color channels must be in [0, 255], got {color!r}.")
    if background_color is not None:
        if len(background_color) != 3 or any(
            not isinstance(c, int) for c in background_color
        ):
            raise ValidationError(
                "background_color must be a 3-tuple of ints, got "
                f"{background_color!r}."
            )
        if any(c < 0 or c > 255 for c in background_color):
            raise ValidationError(
                "background_color channels must be in [0, 255], got "
                f"{background_color!r}."
            )
    if isinstance(font_scale, bool) or not isinstance(font_scale, (int, float)):
        raise ValidationError(f"font_scale must be a number, got {font_scale!r}.")
    if font_scale <= 0:
        raise ValidationError(f"font_scale must be > 0, got {font_scale}.")
    if isinstance(thickness, bool) or not isinstance(thickness, int):
        raise ValidationError(f"thickness must be an int, got {thickness!r}.")
    if thickness < 1:
        raise ValidationError(f"thickness must be >= 1, got {thickness}.")
    if isinstance(padding, bool) or not isinstance(padding, int):
        raise ValidationError(f"padding must be an int, got {padding!r}.")
    if padding < 0:
        raise ValidationError(f"padding must be >= 0, got {padding}.")

    try:
        import cv2
    except ImportError as exc:
        raise AIError(
            "OpenCV (cv2) is required for drawing but is not installed."
        ) from exc

    target = image if inplace else image.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    (text_w, text_h), baseline = cv2.getTextSize(
        text, font, font_scale, thickness
    )
    anchor_x = int(pos_x)
    anchor_y = int(pos_y)

    if background_color is not None:
        rect_x1 = anchor_x - padding
        rect_y1 = anchor_y - text_h - baseline - padding
        rect_x2 = anchor_x + text_w + padding
        rect_y2 = anchor_y + baseline + padding
        cv2.rectangle(
            target,
            (rect_x1, rect_y1),
            (rect_x2, rect_y2),
            background_color,
            -1,
        )

    cv2.putText(
        target,
        text,
        (anchor_x, anchor_y),
        font,
        font_scale,
        color,
        thickness,
        cv2.LINE_AA,
    )
    return target


def draw_detection(
    image: Any,
    detection: Mapping[str, Any],
    *,
    show_confidence: bool = True,
    show_track_id: bool = True,
    inplace: bool = False,
    color: tuple[int, int, int] | None = None,
    thickness: int = _DEFAULT_THICKNESS,
) -> Any:
    """Draw a single detection onto a frame (box + optional label).

    The detection dict follows the project contract::

        {
            "class_name": str,
            "confidence": float,
            "bbox": [x, y, width, height],
            "track_id": str | None,
        }

    Args:
        image: Frame image (BGR).
        detection: Detection dictionary.
        show_confidence: Include the confidence in the label.
        show_track_id: Include the track ID in the label.
        inplace: If ``True``, mutate the source frame.
        color: Optional ``(B, G, R)`` override.  When ``None`` the color
            is derived from the class name.
        thickness: Box line thickness.

    Returns:
        The annotated image.

    Raises:
        ValidationError: If the detection dict is malformed.
        AIError: If OpenCV is unavailable.
    """
    if not isinstance(detection, Mapping):
        raise ValidationError(
            "detection must be a mapping, got "
            f"{type(detection).__name__}."
        )

    class_name = detection.get("class_name")
    bbox = detection.get("bbox")
    confidence = detection.get("confidence")
    track_id = detection.get("track_id")

    if not isinstance(class_name, str) or not class_name.strip():
        raise ValidationError(
            "detection['class_name'] must be a non-empty string."
        )

    _validate_bbox(bbox)  # type: ignore[arg-type]

    if confidence is not None:
        _as_finite_float(confidence, name="detection['confidence']")
        conf = float(confidence)
        if conf < 0.0 or conf > 1.0:
            raise ValidationError(
                f"detection['confidence'] must be in [0, 1], got {conf}."
            )

    box_color = color if color is not None else get_class_color(class_name)

    result = draw_bounding_box(
        image,
        bbox,  # type: ignore[arg-type]
        color=box_color,
        thickness=thickness,
        inplace=inplace,
    )

    label_parts = [class_name]
    if show_confidence and confidence is not None:
        label_parts.append(f"{float(confidence):.2f}")
    if show_track_id and track_id is not None and str(track_id).strip():
        label_parts.append(f"#{track_id}")

    if len(label_parts) > 1:
        label = " ".join(label_parts)
        width, _ = _image_frame(result)
        x, y, w, h = _validate_bbox(bbox)  # type: ignore[arg-type]
        x1, y1, _, _ = _clamp_bbox(x, y, w, h, width, int(getattr(result, "shape")[0]))
        anchor_y = y1 - _DEFAULT_PADDING - 2
        if anchor_y < 0:
            anchor_y = y1 + 2
        result = draw_label(
            result,
            label,
            (x1, anchor_y),
            color=box_color,
            thickness=1,
            padding=_DEFAULT_PADDING,
            inplace=True,
        )

    return result


def draw_detections(
    image: Any,
    detections: Sequence[Mapping[str, Any]],
    *,
    show_confidence: bool = True,
    show_track_id: bool = True,
    inplace: bool = False,
) -> Any:
    """Draw multiple detections onto a single frame.

    Args:
        image: Frame image (BGR).
        detections: Sequence of detection dicts (project contract).
        show_confidence: Include confidence in each label.
        show_track_id: Include track ID in each label.
        inplace: If ``True``, mutate the source frame.

    Returns:
        The annotated image.

    Raises:
        ValidationError: If any detection is malformed.
        AIError: If OpenCV is unavailable.
    """
    if not isinstance(detections, Sequence) or isinstance(detections, (str, bytes)):
        raise ValidationError(
            "detections must be a sequence of detection dicts, got "
            f"{type(detections).__name__}."
        )

    result = image if inplace else image.copy()
    for detection in detections:
        result = draw_detection(
            result,
            detection,
            show_confidence=show_confidence,
            show_track_id=show_track_id,
            inplace=True,
        )
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "get_class_color",
    "draw_bounding_box",
    "draw_label",
    "draw_detection",
    "draw_detections",
]

