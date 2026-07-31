"""VisionOps AI — Unit tests for the ``analysis`` API module and AnalysisService.

Tests:
- Analysis API endpoint schemas
- AnalysisService: detection, aggregation, validation
- Empty dataset, large dataset, edge cases
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from backend.exceptions import (
    FileValidationError,
    StorageError,
    ValidationError,
)


# ===========================================================================
# Analysis API Module
# ===========================================================================


class TestAnalysisAPIImports:
    """Verify analysis-related modules are importable."""

    def test_analysis_api_module(self):
        """The analysis API module can be imported."""
        import backend.api.analysis  # noqa: F401

    def test_analysis_models_module(self):
        """The analysis model module can be imported."""
        import backend.models.analysis  # noqa: F401

    def test_analysis_schemas_module(self):
        """The analysis schema module can be imported."""
        import backend.schemas.analysis  # noqa: F401

    def test_analysis_service_module(self):
        """The analysis_service module can be imported."""
        import backend.services.analysis_service  # noqa: F401


# ===========================================================================
# Analysis Schemas
# ===========================================================================


class TestAnalysisSchemas:
    """Tests for analysis-related Pydantic schemas."""

    def test_analysis_request_schema(self):
        """AnalysisRequest schema exists."""
        from backend.schemas.analysis import AnalysisRequest
        assert AnalysisRequest is not None

    def test_analysis_response_schema(self):
        """AnalysisResponse schema exists."""
        from backend.schemas.analysis import AnalysisResponse
        assert AnalysisResponse is not None


# ===========================================================================
# AnalysisService — Detection
# ===========================================================================


class TestAnalysisServiceDetection:
    """Tests for AnalysisService detection methods."""

    def test_run_detection_success(
        self,
        mock_storage_service: MagicMock,
        sample_raw_detections: list[dict[str, Any]],
    ):
        """run_detection validates, filters, enriches, and persists detections."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        result = service.run_detection(
            video_id="vid_001",
            detections=sample_raw_detections,
            source_frame=1,
        )
        assert len(result) > 0
        assert all(d["detection_id"].startswith("det_") for d in result)
        assert all(d["video_id"] == "vid_001" for d in result)
        mock_storage_service.append_csv_store.assert_called_once()

    def test_run_detection_empty_video_id_raises(self, mock_storage_service: MagicMock):
        """run_detection raises ValidationError for empty video_id."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="video_id must not be empty"):
            service.run_detection(video_id="", detections=[])

    def test_run_detection_invalid_detections_type(self, mock_storage_service: MagicMock):
        """run_detection raises ValidationError for non-list detections."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="detections must be a list"):
            service.run_detection(video_id="vid_001", detections="not_a_list")

    def test_run_detection_storage_error(
        self,
        mock_storage_service: MagicMock,
        sample_raw_detections: list[dict[str, Any]],
    ):
        """run_detection propagates storage service errors."""
        from backend.services.analysis_service import AnalysisService

        mock_storage_service.append_csv_store.side_effect = StorageError("Write failed")
        service = AnalysisService(storage=mock_storage_service)
        with pytest.raises(StorageError, match="Failed to persist detections"):
            service.run_detection(video_id="vid_001", detections=sample_raw_detections)

    def test_run_detection_empty_detections(self, mock_storage_service: MagicMock):
        """run_detection handles empty detections list."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        result = service.run_detection(video_id="vid_001", detections=[])
        assert result == []


# ===========================================================================
# AnalysisService — Detection Validation
# ===========================================================================


class TestAnalysisServiceDetectionValidation:
    """Tests for AnalysisService detection validation methods."""

    def test_validate_detections_all_valid(
        self, mock_storage_service: MagicMock, sample_raw_detections: list[dict[str, Any]],
    ):
        """validate_detections returns all valid detections."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        result = service.validate_detections(sample_raw_detections)
        assert len(result) == 4

    def test_validate_detections_with_invalid(
        self, mock_storage_service: MagicMock, sample_invalid_detections: list[dict[str, Any]],
    ):
        """validate_detections filters out invalid detections."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        result = service.validate_detections(sample_invalid_detections)
        assert len(result) == 0

    def test_validate_detections_empty(self, mock_storage_service: MagicMock):
        """validate_detections returns empty list for empty input."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        result = service.validate_detections([])
        assert result == []


# ===========================================================================
# AnalysisService — Detection Filtering
# ===========================================================================


class TestAnalysisServiceDetectionFiltering:
    """Tests for AnalysisService detection filtering."""

    def test_filter_by_confidence(
        self, mock_storage_service: MagicMock, sample_raw_detections: list[dict[str, Any]],
    ):
        """filter_detections filters by confidence threshold."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        result = service.filter_detections(sample_raw_detections, min_confidence=0.8)
        assert len(result) == 2
        assert all(d["confidence"] >= 0.8 for d in result)

    def test_filter_by_allowed_classes(
        self, mock_storage_service: MagicMock, sample_raw_detections: list[dict[str, Any]],
    ):
        """filter_detections filters by allowed classes."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        result = service.filter_detections(sample_raw_detections, allowed_classes=["forklift"])
        assert len(result) == 1
        assert result[0]["class_name"] == "forklift"

    def test_filter_no_matches(
        self, mock_storage_service: MagicMock, sample_raw_detections: list[dict[str, Any]],
    ):
        """filter_detections returns empty list when nothing matches."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        result = service.filter_detections(
            sample_raw_detections, min_confidence=0.99, allowed_classes=["nonexistent"],
        )
        assert result == []


# ===========================================================================
# AnalysisService — Aggregation
# ===========================================================================


class TestAnalysisServiceAggregation:
    """Tests for AnalysisService aggregation methods."""

    def test_aggregate_results_with_data(self, mock_storage_with_csv_data: MagicMock):
        """aggregate_results returns summary statistics for a video."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_with_csv_data)
        result = service.aggregate_results(video_id="vid_001")
        assert result["video_id"] == "vid_001"
        assert result["total_detections"] > 0
        assert result["unique_classes"] > 0
        assert "class_counts" in result
        assert "average_confidence" in result

    def test_aggregate_results_empty(self, mock_storage_with_csv_data: MagicMock):
        """aggregate_results returns empty summary for video with no detections."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_with_csv_data)
        result = service.aggregate_results(video_id="vid_nonexistent")
        assert result["total_detections"] == 0
        assert result["unique_classes"] == 0
        assert result["class_counts"] == {}
        assert result["average_confidence"] == 0.0

    def test_aggregate_results_empty_video_id_raises(self, mock_storage_service: MagicMock):
        """aggregate_results raises ValidationError for empty video_id."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="video_id must not be empty"):
            service.aggregate_results(video_id="")


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestAnalysisEdgeCases:
    """Edge-case tests for the analysis layer."""

    def test_very_large_confidence_value(self, mock_storage_service: MagicMock):
        """validate_detections filters out-of-range confidence."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        detections = [{"class_name": "test", "confidence": 5.0, "bbox": [0, 0, 10, 10]}]
        result = service.validate_detections(detections)
        assert len(result) == 0

    def test_negative_confidence(self, mock_storage_service: MagicMock):
        """validate_detections filters negative confidence."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        detections = [{"class_name": "test", "confidence": -0.5, "bbox": [0, 0, 10, 10]}]
        result = service.validate_detections(detections)
        assert len(result) == 0

    def test_non_list_bbox(self, mock_storage_service: MagicMock):
        """validate_detections filters non-list bbox."""
        from backend.services.analysis_service import AnalysisService

        service = AnalysisService(storage=mock_storage_service)
        detections = [{"class_name": "test", "confidence": 0.8, "bbox": "not_a_list"}]
        result = service.validate_detections(detections)
        assert len(result) == 0
