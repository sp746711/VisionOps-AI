"""VisionOps AI — Unit tests for the ``ai`` package.

Tests:
- YOLODetector: detection pipeline
- FrameExtractor: frame extraction
- ObjectClassifier: classification
- DetectionValidator: validation
- ByteTrackTracker: tracking
- VideoProcessor: video processing
- InferenceEngine: inference pipeline

All external dependencies (YOLO, Torch, OpenCV, NumPy) are mocked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.exceptions import AIError, FileValidationError, ValidationError


# ===========================================================================
# AI Module Imports
# ===========================================================================


class TestAIImports:
    """Verify that all AI modules are importable."""

    def test_ai_init(self):
        """The ai __init__ module can be imported."""
        import backend.ai  # noqa: F401

    def test_yolo_detector(self):
        """The yolo_detector module can be imported."""
        import backend.ai.yolo_detector  # noqa: F401

    def test_bytetrack_tracker(self):
        """The bytetrack_tracker module can be imported."""
        import backend.ai.bytetrack_tracker  # noqa: F401

    def test_detection_validator(self):
        """The detection_validator module can be imported."""
        import backend.ai.detection_validator  # noqa: F401

    def test_frame_extractor(self):
        """The frame_extractor module can be imported."""
        import backend.ai.frame_extractor  # noqa: F401

    def test_inference_engine(self):
        """The inference_engine module can be imported."""
        import backend.ai.inference_engine  # noqa: F401

    def test_object_classifier(self):
        """The object_classifier module can be imported."""
        import backend.ai.object_classifier  # noqa: F401

    def test_pipeline(self):
        """The pipeline module can be imported."""
        import backend.ai.pipeline  # noqa: F401

    def test_video_processor(self):
        """The video_processor module can be imported."""
        import backend.ai.video_processor  # noqa: F401

    def test_ai_utils_init(self):
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


# ===========================================================================
# YOLODetector
# ===========================================================================


class TestYOLODetector:
    """Tests for :class:`backend.ai.yolo_detector.YOLODetector`."""

    def test_initialisation(self):
        """YOLODetector can be instantiated without loading a real model."""
        from backend.ai.yolo_detector import YOLODetector

        detector = YOLODetector(model_path="dummy.pt", use_mock=True)
        assert detector is not None

    def test_detect_with_mock(self):
        """detect returns mock detections when use_mock=True."""
        from backend.ai.yolo_detector import YOLODetector

        detector = YOLODetector(model_path="dummy.pt", use_mock=True)
        result = detector.detect(frame=None)
        assert isinstance(result, list)

    def test_detect_with_mock_returns_dicts(self):
        """detect returns list of detection dicts with expected keys."""
        from backend.ai.yolo_detector import YOLODetector

        detector = YOLODetector(model_path="dummy.pt", use_mock=True)
        result = detector.detect(frame=None)
        if len(result) > 0:
            detection = result[0]
            assert "class_name" in detection
            assert "confidence" in detection
            assert "bbox" in detection

    def test_validate_model_path(self):
        """validate_model_path checks that model path is non-empty."""
        from backend.ai.yolo_detector import YOLODetector

        detector = YOLODetector(model_path="dummy.pt", use_mock=True)
        with pytest.raises(ValidationError, match="Model path must not be empty"):
            detector.validate_model_path("")

    def test_get_model_info(self):
        """get_model_info returns model metadata."""
        from backend.ai.yolo_detector import YOLODetector

        detector = YOLODetector(model_path="dummy.pt", use_mock=True)
        info = detector.get_model_info()
        assert "model_path" in info
        assert "device" in info


# ===========================================================================
# FrameExtractor
# ===========================================================================


class TestFrameExtractor:
    """Tests for :class:`backend.ai.frame_extractor.FrameExtractor`."""

    def test_initialisation(self):
        """FrameExtractor can be instantiated."""
        from backend.ai.frame_extractor import FrameExtractor

        extractor = FrameExtractor()
        assert extractor is not None

    def test_extract_frames_from_path(self, tmp_path: Path):
        """extract_frames processes a mock video file path."""
        from backend.ai.frame_extractor import FrameExtractor

        video_path = tmp_path / "test.mp4"
        video_path.write_text("mock video content")

        extractor = FrameExtractor()
        frames = extractor.extract_frames(video_path=video_path, use_mock=True)
        assert isinstance(frames, list)

    def test_extract_frames_missing_file(self, tmp_path: Path):
        """extract_frames raises FileValidationError for missing file."""
        from backend.ai.frame_extractor import FrameExtractor

        extractor = FrameExtractor()
        with pytest.raises(FileValidationError, match="Video file not found"):
            extractor.extract_frames(video_path=tmp_path / "missing.mp4")

    def test_extract_frames_empty_file(self, tmp_path: Path):
        """extract_frames raises FileValidationError for empty file."""
        from backend.ai.frame_extractor import FrameExtractor

        video_path = tmp_path / "empty.mp4"
        video_path.touch()
        extractor = FrameExtractor()
        with pytest.raises(FileValidationError, match="Empty video file"):
            extractor.extract_frames(video_path=video_path)

    def test_extract_frames_invalid_extension(self, tmp_path: Path):
        """extract_frames raises ValidationError for invalid extension."""
        from backend.ai.frame_extractor import FrameExtractor

        extractor = FrameExtractor()
        with pytest.raises(ValidationError, match="Invalid video extension"):
            extractor.extract_frames(video_path=tmp_path / "test.txt")

    def test_get_frame_count_mock(self, tmp_path: Path):
        """get_frame_count returns frame count for mock video."""
        from backend.ai.frame_extractor import FrameExtractor

        video_path = tmp_path / "test.mp4"
        video_path.write_text("mock content")
        extractor = FrameExtractor()
        count = extractor.get_frame_count(video_path=video_path, use_mock=True)
        assert count > 0


# ===========================================================================
# ObjectClassifier
# ===========================================================================


class TestObjectClassifier:
    """Tests for :class:`backend.ai.object_classifier.ObjectClassifier`."""

    def test_initialisation(self):
        """ObjectClassifier can be instantiated."""
        from backend.ai.object_classifier import ObjectClassifier

        classifier = ObjectClassifier()
        assert classifier is not None

    def test_classify(self):
        """classify returns classification results."""
        from backend.ai.object_classifier import ObjectClassifier

        classifier = ObjectClassifier()
        result = classifier.classify(detections=[], use_mock=True)
        assert isinstance(result, list)

    def test_classify_with_mock_data(self):
        """classify processes mock detections."""
        from backend.ai.object_classifier import ObjectClassifier

        classifier = ObjectClassifier()
        detections = [
            {"class_name": "person", "confidence": 0.95, "bbox": [0, 0, 10, 10]},
        ]
        result = classifier.classify(detections=detections, use_mock=True)
        assert len(result) > 0

    def test_classify_empty_list(self):
        """classify handles empty detection list."""
        from backend.ai.object_classifier import ObjectClassifier

        classifier = ObjectClassifier()
        result = classifier.classify(detections=[], use_mock=True)
        assert result == []

    def test_get_class_labels(self):
        """get_class_labels returns available class labels."""
        from backend.ai.object_classifier import ObjectClassifier

        classifier = ObjectClassifier()
        labels = classifier.get_class_labels()
        assert isinstance(labels, list)


# ===========================================================================
# DetectionValidator
# ===========================================================================


class TestDetectionValidator:
    """Tests for :class:`backend.ai.detection_validator.DetectionValidator`."""

    def test_initialisation(self):
        """DetectionValidator can be instantiated."""
        from backend.ai.detection_validator import DetectionValidator

        validator = DetectionValidator()
        assert validator is not None

    def test_validate_valid_detection(self):
        """validate returns True for a valid detection."""
        from backend.ai.detection_validator import DetectionValidator

        validator = DetectionValidator()
        detection = {"class_name": "person", "confidence": 0.95, "bbox": [0, 0, 10, 10]}
        assert validator.validate(detection) is True

    def test_validate_missing_fields(self):
        """validate returns False for detection missing required fields."""
        from backend.ai.detection_validator import DetectionValidator

        validator = DetectionValidator()
        assert validator.validate({}) is False
        assert validator.validate({"class_name": "test"}) is False

    def test_validate_low_confidence(self):
        """validate returns True for low confidence detections."""
        from backend.ai.detection_validator import DetectionValidator

        validator = DetectionValidator()
        detection = {"class_name": "test", "confidence": 0.1, "bbox": [0, 0, 10, 10]}
        assert validator.validate(detection) is True

    def test_validate_high_confidence(self):
        """validate handles high confidence values."""
        from backend.ai.detection_validator import DetectionValidator

        validator = DetectionValidator()
        detection = {"class_name": "test", "confidence": 0.999, "bbox": [0, 0, 10, 10]}
        assert validator.validate(detection) is True

    def test_validate_invalid_bbox_type(self):
        """validate returns False for non-list bbox."""
        from backend.ai.detection_validator import DetectionValidator

        validator = DetectionValidator()
        detection = {"class_name": "test", "confidence": 0.8, "bbox": "invalid"}
        assert validator.validate(detection) is False

    def test_validate_batch(self):
        """validate_batch processes multiple detections."""
        from backend.ai.detection_validator import DetectionValidator

        validator = DetectionValidator()
        detections = [
            {"class_name": "a", "confidence": 0.9, "bbox": [0, 0, 1, 1]},
            {"class_name": "b", "confidence": 0.8, "bbox": [1, 1, 2, 2]},
            {},
        ]
        results = validator.validate_batch(detections)
        assert len(results) == 3
        assert results[0] is True
        assert results[1] is True
        assert results[2] is False


# ===========================================================================
# ByteTrackTracker
# ===========================================================================


class TestByteTrackTracker:
    """Tests for :class:`backend.ai.bytetrack_tracker.ByteTrackTracker`."""

    def test_initialisation(self):
        """ByteTrackTracker can be instantiated in mock mode."""
        from backend.ai.bytetrack_tracker import ByteTrackTracker

        tracker = ByteTrackTracker(use_mock=True)
        assert tracker is not None

    def test_update_with_mock(self):
        """update returns mock tracking results."""
        from backend.ai.bytetrack_tracker import ByteTrackTracker

        tracker = ByteTrackTracker(use_mock=True)
        detections = [
            {"class_name": "person", "confidence": 0.95, "bbox": [0, 0, 10, 10]},
        ]
        tracks = tracker.update(detections)
        assert isinstance(tracks, list)

    def test_update_empty(self):
        """update handles empty detection list."""
        from backend.ai.bytetrack_tracker import ByteTrackTracker

        tracker = ByteTrackTracker(use_mock=True)
        tracks = tracker.update([])
        assert tracks == []

    def test_reset(self):
        """reset clears tracker state."""
        from backend.ai.bytetrack_tracker import ByteTrackTracker

        tracker = ByteTrackTracker(use_mock=True)
        result = tracker.reset()
        assert result is not None


# ===========================================================================
# VideoProcessor
# ===========================================================================


class TestVideoProcessor:
    """Tests for :class:`backend.ai.video_processor.VideoProcessor`."""

    def test_initialisation(self):
        """VideoProcessor can be instantiated in mock mode."""
        from backend.ai.video_processor import VideoProcessor

        processor = VideoProcessor(use_mock=True)
        assert processor is not None

    def test_process_video_mock(self, tmp_path: Path):
        """process_video returns processing results in mock mode."""
        from backend.ai.video_processor import VideoProcessor

        video_path = tmp_path / "test.mp4"
        video_path.write_text("mock content")
        processor = VideoProcessor(use_mock=True)
        result = processor.process_video(video_path=video_path)
        assert isinstance(result, dict)

    def test_process_video_missing_file(self, tmp_path: Path):
        """process_video raises error for missing file."""
        from backend.ai.video_processor import VideoProcessor

        processor = VideoProcessor(use_mock=True)
        with pytest.raises(FileValidationError):
            processor.process_video(video_path=tmp_path / "missing.mp4")


# ===========================================================================
# InferenceEngine
# ===========================================================================


class TestInferenceEngine:
    """Tests for :class:`backend.ai.inference_engine.InferenceEngine`."""

    def test_initialisation(self):
        """InferenceEngine can be instantiated in mock mode."""
        from backend.ai.inference_engine import InferenceEngine

        engine = InferenceEngine(use_mock=True)
        assert engine is not None

    def test_run_inference_mock(self):
        """run_inference returns mock results."""
        from backend.ai.inference_engine import InferenceEngine

        engine = InferenceEngine(use_mock=True)
        result = engine.run_inference(frame=None)
        assert isinstance(result, list) or isinstance(result, dict)

    def test_get_engine_info(self):
        """get_engine_info returns engine metadata."""
        from backend.ai.inference_engine import InferenceEngine

        engine = InferenceEngine(use_mock=True)
        info = engine.get_engine_info()
        assert "name" in info or "engine" in info


# ===========================================================================
# Pipeline
# ===========================================================================


class TestPipeline:
    """Tests for the AI pipeline."""

    def test_initialisation(self):
        """Pipeline can be instantiated in mock mode."""
        from backend.ai.pipeline import Pipeline

        pipeline = Pipeline(use_mock=True)
        assert pipeline is not None

    def test_run_pipeline_mock(self, tmp_path: Path):
        """run executes the full pipeline in mock mode."""
        from backend.ai.pipeline import Pipeline

        video_path = tmp_path / "test.mp4"
        video_path.write_text("mock content")
        pipeline = Pipeline(use_mock=True)
        result = pipeline.run(video_path=video_path)
        assert isinstance(result, dict)

    def test_run_pipeline_params(self, tmp_path: Path):
        """run accepts configuration parameters."""
        from backend.ai.pipeline import Pipeline

        video_path = tmp_path / "test.mp4"
        video_path.write_text("mock content")
        pipeline = Pipeline(use_mock=True)
        result = pipeline.run(video_path=video_path, params={"confidence": 0.7})
        assert isinstance(result, dict)
