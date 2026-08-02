"""VisionOps AI — AI / Computer-Vision package.

Provides the production-ready AI inference layer for the VisionOps AI
platform:

* YOLO-based object detection (:mod:`backend.ai.yolo_detector`)
* ByteTrack-based multi-object tracking (:mod:`backend.ai.bytetrack_tracker`)
* detection validation (:mod:`backend.ai.detection_validator`)
* frame extraction (:mod:`backend.ai.frame_extractor`)
* class normalization (:mod:`backend.ai.object_classifier`)
* AI pipeline orchestration (:mod:`backend.ai.inference_engine`)
* video processing (:mod:`backend.ai.video_processor`)
* high-level facade (:mod:`backend.ai.pipeline`)
* visualization / image / video utilities (:mod:`backend.ai.utils`)

Lazy loading
------------
Public names are exported lazily via :pep:`562` ``__getattr__`` — the same
pattern used by :mod:`backend.models`.  This guarantees that::

    import backend.ai

never triggers:

* YOLO model loading
* CUDA / PyTorch initialization
* OpenCV video processing
* model downloads
* any expensive import-time work

Heavy dependencies (torch, ultralytics, bytetrack) are imported lazily by
the individual modules only when those features are actually used.

This package is intentionally independent from ``backend.api``,
``backend.middleware``, dashboard logic, Power BI logic, and HTTP request
handling.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

# ---------------------------------------------------------------------------
# Lazy export registry — maps public name -> (module path, attribute name)
# ---------------------------------------------------------------------------

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "YOLODetector": ("backend.ai.yolo_detector", "YOLODetector"),
    "ByteTrackTracker": ("backend.ai.bytetrack_tracker", "ByteTrackTracker"),
    "DetectionValidator": ("backend.ai.detection_validator", "DetectionValidator"),
    "FrameExtractor": ("backend.ai.frame_extractor", "FrameExtractor"),
    "ObjectClassifier": ("backend.ai.object_classifier", "ObjectClassifier"),
    "InferenceEngine": ("backend.ai.inference_engine", "InferenceEngine"),
    "VideoProcessor": ("backend.ai.video_processor", "VideoProcessor"),
    "Pipeline": ("backend.ai.pipeline", "Pipeline"),
    "AIPipeline": ("backend.ai.pipeline", "AIPipeline"),
    "run_pipeline": ("backend.ai.pipeline", "run_pipeline"),
}

#: Public API of the AI package.
__all__ = sorted(_LAZY_EXPORTS)

# Forward references for static type checkers / IDE autocompletion.
if TYPE_CHECKING:  # pragma: no cover
    from backend.ai.bytetrack_tracker import ByteTrackTracker as ByteTrackTracker
    from backend.ai.detection_validator import DetectionValidator as DetectionValidator
    from backend.ai.frame_extractor import FrameExtractor as FrameExtractor
    from backend.ai.inference_engine import InferenceEngine as InferenceEngine
    from backend.ai.object_classifier import ObjectClassifier as ObjectClassifier
    from backend.ai.pipeline import AIPipeline as AIPipeline
    from backend.ai.pipeline import Pipeline as Pipeline
    from backend.ai.pipeline import run_pipeline as run_pipeline
    from backend.ai.video_processor import VideoProcessor as VideoProcessor
    from backend.ai.yolo_detector import YOLODetector as YOLODetector


# ---------------------------------------------------------------------------
# PEP 562 lazy attribute access
# ---------------------------------------------------------------------------


def __getattr__(name: str) -> object:
    """Lazily import and return an AI class/function by name.

    Invoked by Python only when *name* is not found as a regular module
    attribute.  Delegates to the registry :data:`_LAZY_EXPORTS` to import
    the owning submodule and return the requested attribute.

    Args:
        name: The requested public AI name.

    Returns:
        The requested class/function.

    Raises:
        AttributeError: If *name* is not a known AI export.
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
        Sorted union of the module's own attributes and the lazily
        exported AI names.
    """
    return sorted({*globals().keys(), *_LAZY_EXPORTS})

