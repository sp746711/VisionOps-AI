"""VisionOps AI — Image utility helpers for the AI layer.

Provides dependency-light helpers for working with image frames:

- image validation and dimension inspection
- aspect-ratio-preserving resizing / letterboxing
- numeric normalization (uint8 → float, float → uint8)
- BGR ↔ RGB color-space conversion
- safe image loading from disk

Design notes
------------
* NumPy and OpenCV are imported lazily inside functions so that merely
  importing this module never requires those optional dependencies.
* ``normalize_image`` is provided for callers that need explicit
  normalization; the YOLO adapter does **not** duplicate Ultralytics'
  built-in preprocessing.
* All helpers validate inputs and raise
  :class:`~backend.exceptions.ValidationError` for malformed images and
  :class:`~backend.exceptions.AIError` for unavailable optional
  dependencies.

This module intentionally avoids business rules, persistence, and API
concerns.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

from backend.exceptions import AIError, FileValidationError, ValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Expected channel order for OpenCV frames.
BGR_CHANNELS: int = 3
#: Grayscale channel count.
GRAY_CHANNELS: int = 1


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------


def _as_number(value: object, *, name: str) -> float:
    """Convert a value to a finite float, rejecting non-numeric values.

    Args:
        value: Value to convert (NumPy scalars are accepted).
        name: Field name for error messages.

    Returns:
        The finite float value.

    Raises:
        ValidationError: If *value* is not a finite real number.
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


# ---------------------------------------------------------------------------
# Image validation
# ---------------------------------------------------------------------------


def validate_image(image: Any) -> tuple[int, int]:
    """Validate an image array and return its ``(height, width)``.

    Accepts either a NumPy ``ndarray`` or a duck-typed object exposing a
    ``shape`` attribute with at least 2 positive integer dimensions.

    Args:
        image: Image array (BGR uint8 expected for OpenCV frames).

    Returns:
        ``(height, width)`` tuple derived from ``image.shape``.

    Raises:
        ValidationError: If the image is not a valid array.
        AIError: If NumPy is unavailable.
    """
    shape = getattr(image, "shape", None)
    if shape is None:
        raise ValidationError(
            "Image must expose a 'shape' attribute (e.g. numpy.ndarray), "
            f"got {type(image).__name__}."
        )

    if len(shape) < 2:
        raise ValidationError(
            f"Image must have at least 2 dimensions, got {len(shape)}."
        )

    height, width = int(shape[0]), int(shape[1])
    if height <= 0 or width <= 0:
        raise ValidationError(
            f"Image dimensions must be positive, got ({height}, {width})."
        )

    return height, width


def is_valid_image(image: Any) -> bool:
    """Return ``True`` if *image* looks like a valid array.

    This is a non-raising convenience wrapper around :func:`validate_image`.

    Args:
        image: Candidate image array.

    Returns:
        ``True`` if the image has a valid shape with positive dimensions.
    """
    try:
        validate_image(image)
        return True
    except (ValidationError, AIError):
        return False


def get_image_dimensions(image: Any) -> dict[str, int]:
    """Return dimension metadata for an image.

    Args:
        image: Image array.

    Returns:
        Dictionary with keys ``height``, ``width``, ``channels`` and
        ``dtype`` (as ``str`` or ``None``).

    Raises:
        ValidationError: If the image is invalid.
    """
    height, width = validate_image(image)
    shape = getattr(image, "shape")
    channels = int(shape[2]) if len(shape) >= 3 else GRAY_CHANNELS
    dtype = getattr(getattr(image, "dtype", None), "__name__", None)
    return {
        "height": height,
        "width": width,
        "channels": channels,
        "dtype": dtype,
    }


# ---------------------------------------------------------------------------
# Resize / letterbox
# ---------------------------------------------------------------------------


def resize_image(
    image: Any,
    width: int,
    height: int,
    *,
    keep_aspect_ratio: bool = False,
    interpolation: int | None = None,
) -> Any:
    """Resize an image to the requested dimensions.

    Args:
        image: Image array (BGR).
        width: Target width (>= 1).
        height: Target height (>= 1).
        keep_aspect_ratio: If ``True``, preserve the source aspect ratio
            and pad with black borders to exactly fit *width* x *height*.
        interpolation: Optional OpenCV interpolation constant.  When
            ``None``, a sensible default is chosen based on whether the
            image is being up- or down-scaled.

    Returns:
        The resized image (same channel layout as the input).

    Raises:
        ValidationError: If dimensions are invalid.
        AIError: If OpenCV is unavailable.
    """
    validate_image(image)
    if isinstance(width, bool) or not isinstance(width, int):
        raise ValidationError(f"width must be an integer, got {width!r}.")
    if isinstance(height, bool) or not isinstance(height, int):
        raise ValidationError(f"height must be an integer, got {height!r}.")
    if width < 1 or height < 1:
        raise ValidationError(
            f"Target dimensions must be >= 1, got ({width}, {height})."
        )

    try:
        import cv2
    except ImportError as exc:
        raise AIError(
            "OpenCV (cv2) is required for image resizing but is not "
            "installed."
        ) from exc

    if keep_aspect_ratio:
        return letterbox_image(
            image,
            target_width=width,
            target_height=height,
            interpolation=interpolation,
        )

    if interpolation is None:
        h, w = validate_image(image)
        if width > w or height > h:
            interpolation = cv2.INTER_LINEAR
        else:
            interpolation = cv2.INTER_AREA

    try:
        return cv2.resize(image, (width, height), interpolation=interpolation)
    except Exception as exc:
        raise AIError(f"Failed to resize image: {exc}") from exc


def letterbox_image(
    image: Any,
    *,
    target_width: int = 640,
    target_height: int = 640,
    interpolation: int | None = None,
    color: tuple[int, int, int] = (114, 114, 114),
) -> Any:
    """Resize an image preserving aspect ratio and pad to the target box.

    Args:
        image: Image array (BGR).
        target_width: Target canvas width (>= 1).
        target_height: Target canvas height (>= 1).
        interpolation: Optional OpenCV interpolation constant.
        color: Border fill color as ``(B, G, R)`` (default: gray).

    Returns:
        A ``(target_height, target_width, channels)`` image with the
        original content letterboxed onto it.

    Raises:
        ValidationError: If dimensions or color are invalid.
        AIError: If OpenCV/NumPy are unavailable or resizing fails.
    """
    src_height, src_width = validate_image(image)
    if target_width < 1 or target_height < 1:
        raise ValidationError(
            "Target dimensions must be >= 1, got "
            f"({target_width}, {target_height})."
        )
    if len(color) != 3 or any(not isinstance(c, int) for c in color):
        raise ValidationError(
            f"color must be a 3-tuple of ints, got {color!r}."
        )
    if any(c < 0 or c > 255 for c in color):
        raise ValidationError(
            f"color channels must be in [0, 255], got {color!r}."
        )

    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise AIError(
            "OpenCV and NumPy are required for letterboxing but are not "
            "installed."
        ) from exc

    if interpolation is None:
        interpolation = (
            cv2.INTER_LINEAR
            if target_width > src_width or target_height > src_height
            else cv2.INTER_AREA
        )

    # Compute scale factor preserving aspect ratio.
    scale = min(
        float(target_width) / float(src_width),
        float(target_height) / float(src_height),
    )
    new_width = max(int(round(src_width * scale)), 1)
    new_height = max(int(round(src_height * scale)), 1)

    try:
        resized = cv2.resize(
            image,
            (new_width, new_height),
            interpolation=interpolation,
        )
        canvas = np.full(
            (target_height, target_width, resized.shape[2]),
            color,
            dtype=resized.dtype,
        )
        offset_x = (target_width - new_width) // 2
        offset_y = (target_height - new_height) // 2
        canvas[offset_y:offset_y + new_height, offset_x:offset_x + new_width] = resized
        return canvas
    except Exception as exc:
        raise AIError(f"Failed to letterbox image: {exc}") from exc


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------


def ensure_uint8(image: Any) -> Any:
    """Return the image as an unsigned 8-bit array.

    Floating-point inputs in ``[0.0, 1.0]`` are scaled by 255; other
    numeric dtypes are clipped to ``[0, 255]`` and cast.

    Args:
        image: Image array.

    Returns:
        A ``uint8`` image array.

    Raises:
        ValidationError: If the image is invalid.
        AIError: If NumPy is unavailable or conversion fails.
    """
    validate_image(image)
    try:
        import numpy as np
    except ImportError as exc:
        raise AIError(
            "NumPy is required for image conversion but is not installed."
        ) from exc

    dtype = getattr(getattr(image, "dtype", None), "__name__", None)
    if dtype == "uint8":
        return image

    try:
        if np.issubdtype(getattr(image, "dtype", np.float32), np.floating):
            return np.clip(image * 255.0, 0, 255).astype(np.uint8)
        return np.clip(image, 0, 255).astype(np.uint8)
    except Exception as exc:
        raise AIError(f"Failed to convert image to uint8: {exc}") from exc


def ensure_float32(image: Any) -> Any:
    """Return the image as a float32 array in ``[0.0, 1.0]``.

    uint8 inputs are divided by 255; other numeric dtypes are converted
    directly (clipped to ``[0, 1]`` only when the source is uint8).

    Args:
        image: Image array.

    Returns:
        A ``float32`` image array.

    Raises:
        ValidationError: If the image is invalid.
        AIError: If NumPy is unavailable or conversion fails.
    """
    validate_image(image)
    try:
        import numpy as np
    except ImportError as exc:
        raise AIError(
            "NumPy is required for image conversion but is not installed."
        ) from exc

    dtype = getattr(getattr(image, "dtype", None), "__name__", None)
    try:
        if dtype == "uint8":
            return image.astype(np.float32) / 255.0
        return image.astype(np.float32)
    except Exception as exc:
        raise AIError(f"Failed to convert image to float32: {exc}") from exc


def normalize_image(
    image: Any,
    *,
    mean: float = 0.0,
    std: float = 1.0,
) -> Any:
    """Normalize an image by ``(image - mean) / std``.

    Args:
        image: Image array (typically float32 in ``[0, 1]``).
        mean: Mean subtraction value (default: 0.0).
        std: Standard deviation divisor (must be > 0).

    Returns:
        The normalized image array (same dtype as input).

    Raises:
        ValidationError: If *std* is not positive.
        AIError: If NumPy is unavailable or normalization fails.
    """
    validate_image(image)
    std_val = _as_number(std, name="std")
    _ = _as_number(mean, name="mean")
    if std_val <= 0.0:
        raise ValidationError(f"std must be > 0, got {std_val}.")

    try:
        import numpy as np
    except ImportError as exc:
        raise AIError(
            "NumPy is required for image normalization but is not installed."
        ) from exc

    try:
        return (image.astype(np.float32) - float(mean)) / float(std_val)
    except Exception as exc:
        raise AIError(f"Failed to normalize image: {exc}") from exc


# ---------------------------------------------------------------------------
# Color-space conversion
# ---------------------------------------------------------------------------


def bgr_to_rgb(image: Any) -> Any:
    """Convert a BGR image to RGB.

    Args:
        image: BGR image array with exactly 3 channels.

    Returns:
        RGB image array.

    Raises:
        ValidationError: If the image is invalid or does not have 3
            channels.
        AIError: If OpenCV is unavailable or conversion fails.
    """
    info = get_image_dimensions(image)
    if info["channels"] != BGR_CHANNELS:
        raise ValidationError(
            "BGR-to-RGB conversion requires a 3-channel image, got "
            f"{info['channels']} channel(s)."
        )
    try:
        import cv2
    except ImportError as exc:
        raise AIError(
            "OpenCV (cv2) is required for color-space conversion but is "
            "not installed."
        ) from exc
    try:
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    except Exception as exc:
        raise AIError(f"Failed to convert BGR to RGB: {exc}") from exc


def rgb_to_bgr(image: Any) -> Any:
    """Convert an RGB image to BGR.

    Args:
        image: RGB image array with exactly 3 channels.

    Returns:
        BGR image array.

    Raises:
        ValidationError: If the image is invalid or does not have 3
            channels.
        AIError: If OpenCV is unavailable or conversion fails.
    """
    info = get_image_dimensions(image)
    if info["channels"] != BGR_CHANNELS:
        raise ValidationError(
            "RGB-to-BGR conversion requires a 3-channel image, got "
            f"{info['channels']} channel(s)."
        )
    try:
        import cv2
    except ImportError as exc:
        raise AIError(
            "OpenCV (cv2) is required for color-space conversion but is "
            "not installed."
        ) from exc
    try:
        return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    except Exception as exc:
        raise AIError(f"Failed to convert RGB to BGR: {exc}") from exc


# ---------------------------------------------------------------------------
# Safe loading
# ---------------------------------------------------------------------------


def safe_imread(path: str | Path) -> Any:
    """Safely load an image from disk as BGR uint8.

    Args:
        path: Path to an image file.

    Returns:
        The decoded BGR image array.

    Raises:
        FileValidationError: If the file does not exist or is empty.
        AIError: If OpenCV is unavailable, the file cannot be decoded, or
            decoding produces a ``None`` result.
    """
    image_path = Path(path)
    if not image_path.is_file():
        raise FileValidationError(f"Image file not found: '{image_path}'.")
    if image_path.stat().st_size == 0:
        raise FileValidationError(f"Empty image file: '{image_path}'.")

    try:
        import cv2
    except ImportError as exc:
        raise AIError(
            "OpenCV (cv2) is required for image loading but is not "
            "installed."
        ) from exc

    image = cv2.imread(str(image_path))
    if image is None:
        raise AIError(
            f"Failed to decode image file '{image_path}'. The file may "
            "be corrupt or in an unsupported format."
        )
    return image


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "BGR_CHANNELS",
    "GRAY_CHANNELS",
    "validate_image",
    "is_valid_image",
    "get_image_dimensions",
    "resize_image",
    "letterbox_image",
    "ensure_uint8",
    "ensure_float32",
    "normalize_image",
    "bgr_to_rgb",
    "rgb_to_bgr",
    "safe_imread",
]

