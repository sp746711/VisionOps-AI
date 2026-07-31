"""VisionOps AI — Sanity tests for the ``ai`` package.

The AI package modules are currently stubs (zero bytes).
These tests verify that the modules can be imported and their
expected public symbols are accessible.
"""

from __future__ import annotations

import pytest


class TestAIPackage:
    """Sanity checks for the ai package."""

    def test_ai_init_module(self):
        """The ai __init__ module can be imported."""
        import backend.ai  # noqa: F401

    def test_yolo_detector_module(self):
        """The yolo_detector module can be imported."""
        import backend.ai.yolo_detector  # noqa: F401

    def test_bytetrack_tracker_module(self):
        """The bytetrack_tracker module can be imported."""
        import backend.ai.bytetrack_tracker  # noqa: F401

    def test_detection_validator_module(self):
        """The detection_validator module can be imported."""
        import backend.ai.detection_validator  # noqa: F401

    def test_frame_extractor_module(self):
        """The frame_extractor module can be imported."""
        import backend.ai.frame_extractor  # noqa: F401

    def test_inference_engine_module(self):
        """The inference_engine module can be imported."""
        import backend.ai.inference_engine  # noqa: F401

    def test_object_classifier_module(self):
        """The object_classifier module can be imported."""
        import backend.ai.object_classifier  # noqa: F401

    def test_pipeline_module(self):
        """The pipeline module can be imported."""
        import backend.ai.pipeline  # noqa: F401

    def test_video_processor_module(self):
        """The video_processor module can be imported."""
        import backend.ai.video_processor  # noqa: F401


class TestAIUtilsPackage:
    """Sanity checks for the ai utils subpackage."""

    def test_ai_utils_init_module(self):
        """The ai utils __init__ module can be imported."""
        import backend.ai.utils  # noqa: F401

    def test_drawing_module(self):
        """The drawing module can be imported."""
        import backend.ai.utils.drawing  # noqa: F401

    def test_image_utils_module(self):
        """The image_utils module can be imported."""
        import backend.ai.utils.image_utils  # noqa: F401

    def test_video_utils_module(self):
        """The video_utils module can be imported."""
        import backend.ai.utils.video_utils  # noqa: F401
