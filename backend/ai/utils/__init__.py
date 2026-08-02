"""VisionOps AI — AI utility helpers package.

This sub-package contains lightweight, dependency-light helpers used by
the AI layer:

- :mod:`backend.ai.utils.video_utils` — video validation, metadata
  inspection, safe frame iteration, and capture lifecycle helpers.
- :mod:`backend.ai.utils.image_utils` — image validation, resizing,
  normalization, and color-space conversion helpers.
- :mod:`backend.ai.utils.drawing` — bounding-box/label annotation
  helpers for visualization.

Import safety
-------------
This ``__init__`` intentionally performs **no** eager imports of heavy AI
libraries (OpenCV, NumPy, Torch, Ultralytics, ByteTrack).  Public helpers
are re-exported lazily via :pep:`562` ``__getattr__`` so that::

    import backend.ai.utils

succeeds even in environments where optional AI dependencies are not
installed.  The actual imports happen only when a helper is accessed.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

# ---------------------------------------------------------------------------
# Lazy export registry — maps public name -> (module path, attribute name)
# ---------------------------------------------------------------------------

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    # video_utils
    "SUPPORTED_VIDEO_EXTENSIONS": (
        "backend.ai.utils.video_utils",
        "SUPPORTED_VIDEO_EXTENSIONS",
    ),
    "is_supported_video": ("backend.ai.utils.video_utils", "is_supported_video"),
    "validate_video_file": (
        "backend.ai.utils.video_utils",
        "validate_video_file",
    ),
    "open_video": ("backend.ai.utils.video_utils", "open_video"),
    "close_video": ("backend.ai.utils.video_utils", "close_video"),
    "get_video_info": ("backend.ai.utils.video_utils", "get_video_info"),
    "iter_video_frames": ("backend.ai.utils.video_utils", "iter_video_frames"),
    "frame_index_to_timestamp": (
        "backend.ai.utils.video_utils",
        "frame_index_to_timestamp",
    ),
    # image_utils
    "is_valid_image": ("backend.ai.utils.image_utils", "is_valid_image"),
    "validate_image": ("backend.ai.utils.image_utils", "validate_image"),
    "get_image_dimensions": (
        "backend.ai.utils.image_utils",
        "get_image_dimensions",
    ),
    "resize_image": ("backend.ai.utils.image_utils", "resize_image"),
    "letterbox_image": ("backend.ai.utils.image_utils", "letterbox_image"),
    "normalize_image": ("backend.ai.utils.image_utils", "normalize_image"),
    "bgr_to_rgb": ("backend.ai.utils.image_utils", "bgr_to_rgb"),
    "rgb_to_bgr": ("backend.ai.utils.image_utils", "rgb_to_bgr"),
    "safe_imread": ("backend.ai.utils.image_utils", "safe_imread"),
    "ensure_uint8": ("backend.ai.utils.image_utils", "ensure_uint8"),
    "ensure_float32": ("backend.ai.utils.image_utils", "ensure_float32"),
    # drawing
    "draw_bounding_box": ("backend.ai.utils.drawing", "draw_bounding_box"),
    "draw_label": ("backend.ai.utils.drawing", "draw_label"),
    "draw_detection": ("backend.ai.utils.drawing", "draw_detection"),
    "draw_detections": ("backend.ai.utils.drawing", "draw_detections"),
    "get_class_color": ("backend.ai.utils.drawing", "get_class_color"),
}

#: Public API of the AI utils package.
__all__ = sorted(_LAZY_EXPORTS)

# Forward references for static type checkers and IDE autocompletion.
if TYPE_CHECKING:  # pragma: no cover
    from backend.ai.utils.drawing import (
        draw_bounding_box as draw_bounding_box,
        draw_detection as draw_detection,
        draw_detections as draw_detections,
        draw_label as draw_label,
        get_class_color as get_class_color,
    )
    from backend.ai.utils.image_utils import (
        bgr_to_rgb as bgr_to_rgb,
        ensure_float32 as ensure_float32,
        ensure_uint8 as ensure_uint8,
        get_image_dimensions as get_image_dimensions,
        is_valid_image as is_valid_image,
        letterbox_image as letterbox_image,
        normalize_image as normalize_image,
        resize_image as resize_image,
        rgb_to_bgr as rgb_to_bgr,
        safe_imread as safe_imread,
        validate_image as validate_image,
    )
    from backend.ai.utils.video_utils import (
        SUPPORTED_VIDEO_EXTENSIONS as SUPPORTED_VIDEO_EXTENSIONS,
        close_video as close_video,
        frame_index_to_timestamp as frame_index_to_timestamp,
        get_video_info as get_video_info,
        is_supported_video as is_supported_video,
        iter_video_frames as iter_video_frames,
        open_video as open_video,
        validate_video_file as validate_video_file,
    )


# ---------------------------------------------------------------------------
# PEP 562 lazy attribute access
# ---------------------------------------------------------------------------


def __getattr__(name: str) -> object:
    """Lazily import and return a utility by name.

    Args:
        name: The requested public utility name.

    Returns:
        The requested helper (function, class, or constant).

    Raises:
        AttributeError: If *name* is not a known public export.
    """
    entry = _LAZY_EXPORTS.get(name)
    if entry is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = entry
    module = importlib.import_module(module_name)
    return getattr(module, attribute_name)


def __dir__() -> list[str]:
    """Return the complete public attribute listing for IDE support.

    Returns:
        Sorted union of the module's own attributes and lazily exported
        helper names.
    """
    return sorted({*globals().keys(), *_LAZY_EXPORTS})

