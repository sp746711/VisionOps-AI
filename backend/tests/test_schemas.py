"""VisionOps AI — Unit tests for the ``schemas`` package.

Tests cover:
- Importability of every schema module and class
- Schema instantiation with valid data
- Validation rejection of invalid data
- The ``__init__.py`` re-export mechanism
- Edge cases (empty strings, out-of-range values, missing fields)

All schemas use Pydantic v2 and are tested via direct instantiation.
"""

from __future__ import annotations

import datetime
from typing import Any

import pytest
from pydantic import ValidationError

# ===========================================================================
# Common Schemas
# ===========================================================================


class TestCommonSchemas:
    """Tests for backend.schemas.common."""

    def test_base_schema_import(self):
        """BaseSchema is importable."""
        from backend.schemas.common import BaseSchema
        assert BaseSchema is not None

    def test_enums_import(self):
        """All enums are importable."""
        from backend.schemas.common import (
            Severity, VideoStatus, ReportFormat, UserRole,
            PipelineOperation, DetectionClass,
        )
        assert Severity.LOW.value == "low"
        assert VideoStatus.UPLOADED.value == "uploaded"
        assert ReportFormat.PDF.value == "pdf"
        assert UserRole.ADMIN.value == "admin"
        assert PipelineOperation.FULL_PIPELINE.value == "full_pipeline"
        assert DetectionClass.PERSON.value == "person"

    def test_bounding_box_valid(self):
        """BoundingBox accepts valid coordinates."""
        from backend.schemas.common import BoundingBox
        bbox = BoundingBox(x=10.0, y=20.0, width=50.0, height=100.0)
        assert bbox.x == 10.0
        assert bbox.as_list() == [10.0, 20.0, 50.0, 100.0]

    def test_bounding_box_from_list(self):
        """BoundingBox.from_list creates a valid instance."""
        from backend.schemas.common import BoundingBox
        bbox = BoundingBox.from_list([1.0, 2.0, 3.0, 4.0])
        assert bbox.x == 1.0
        assert bbox.width == 3.0

    def test_bounding_box_invalid_dimensions(self):
        """BoundingBox rejects zero/negative dimensions."""
        from backend.schemas.common import BoundingBox
        with pytest.raises(ValidationError):
            BoundingBox(x=0, y=0, width=0, height=0)

    def test_bounding_box_from_list_wrong_length(self):
        """BoundingBox.from_list rejects wrong-length sequences."""
        from backend.schemas.common import BoundingBox
        with pytest.raises(ValueError, match="exactly 4"):
            BoundingBox.from_list([1.0, 2.0, 3.0])

    def test_time_range_valid(self):
        """TimeRange accepts valid ordered timestamps."""
        from backend.schemas.common import TimeRange
        now = datetime.datetime.now(datetime.timezone.utc)
        tr = TimeRange(start=now, end=now + datetime.timedelta(hours=1))
        assert tr.start == now

    def test_time_range_reversed(self):
        """TimeRange rejects reversed (start > end) ranges."""
        from backend.schemas.common import TimeRange
        now = datetime.datetime.now(datetime.timezone.utc)
        with pytest.raises(ValidationError, match="must not be after"):
            TimeRange(start=now + datetime.timedelta(hours=1), end=now)

    def test_pagination_params_defaults(self):
        """PaginationParams has sane defaults."""
        from backend.schemas.common import PaginationParams
        p = PaginationParams()
        assert p.limit == 100
        assert p.offset == 0

    def test_date_range_filter_valid(self):
        """DateRangeFilter accepts valid ordered dates."""
        from backend.schemas.common import DateRangeFilter
        dr = DateRangeFilter(date_from="2025-01-01", date_to="2025-01-31")
        assert dr.date_from == "2025-01-01"

    def test_date_range_filter_reversed(self):
        """DateRangeFilter rejects reversed dates."""
        from backend.schemas.common import DateRangeFilter
        with pytest.raises(ValidationError, match="must not be after"):
            DateRangeFilter(date_from="2025-02-01", date_to="2025-01-01")


# ===========================================================================
# Response Schemas
# ===========================================================================


class TestResponseSchemas:
    """Tests for backend.schemas.response."""

    def test_success_response(self):
        """SuccessResponse can be instantiated with data."""
        from backend.schemas.response import SuccessResponse
        resp = SuccessResponse(data={"key": "value"}, message="OK")
        assert resp.data["key"] == "value"
        assert resp.message == "OK"
        assert resp.success is True

    def test_error_response(self):
        """ErrorResponse can be instantiated with error details."""
        from backend.schemas.response import ErrorResponse
        resp = ErrorResponse(error_code="NOT_FOUND", message="Resource not found")
        assert resp.error_code == "NOT_FOUND"
        assert resp.message == "Resource not found"
        assert resp.success is False

    def test_paginated_response(self):
        """PaginatedResponse includes pagination metadata."""
        from backend.schemas.response import PaginatedResponse
        resp = PaginatedResponse(
            items=[1, 2, 3],
            total=100,
            limit=10,
            offset=0,
        )
        assert resp.total == 100
        assert len(resp.items) == 3


# ===========================================================================
# Auth Schemas
# ===========================================================================


class TestAuthSchemas:
    """Tests for backend.schemas.auth."""

    def test_login_request_valid(self):
        """LoginRequest accepts valid credentials."""
        from backend.schemas.auth import LoginRequest
        lr = LoginRequest(username="admin", password="admin123")
        assert lr.username == "admin"

    def test_login_request_empty_username(self):
        """LoginRequest rejects empty username."""
        from backend.schemas.auth import LoginRequest
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="pass")

    def test_login_request_empty_password(self):
        """LoginRequest rejects empty password."""
        from backend.schemas.auth import LoginRequest
        with pytest.raises(ValidationError):
            LoginRequest(username="admin", password="")

    def test_register_request_valid(self):
        """RegisterRequest accepts valid registration data."""
        from backend.schemas.auth import RegisterRequest
        rr = RegisterRequest(
            username="newuser",
            email="user@example.com",
            password="SecurePass123",
        )
        assert rr.username == "newuser"

    def test_register_request_weak_password(self):
        """RegisterRequest rejects weak passwords."""
        from backend.schemas.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(
                username="newuser",
                email="user@example.com",
                password="short",
            )

    def test_token_response_valid(self):
        """TokenResponse accepts valid token data."""
        from backend.schemas.auth import TokenResponse
        tr = TokenResponse(access_token="abc.def.ghi", expires_in=3600)
        assert tr.token_type == "bearer"
        assert tr.expires_in == 3600

    def test_user_response_valid(self):
        """UserResponse accepts valid user data."""
        from backend.schemas.auth import UserResponse
        now = datetime.datetime.now(datetime.timezone.utc)
        ur = UserResponse(
            user_id="u1",
            username="admin",
            email="admin@example.com",
            role="admin",
            created_at=now,
        )
        assert ur.role.value == "admin"


# ===========================================================================
# Video Schemas
# ===========================================================================


class TestVideoSchemas:
    """Tests for backend.schemas.video."""

    def test_upload_request_valid(self):
        """VideoUploadRequest accepts valid upload data."""
        from backend.schemas.video import VideoUploadRequest
        ur = VideoUploadRequest(filename="video.mp4", file_size=1048576)
        assert ur.filename == "video.mp4"

    def test_upload_request_bad_extension(self):
        """VideoUploadRequest rejects disallowed extensions."""
        from backend.schemas.video import VideoUploadRequest
        with pytest.raises(ValidationError):
            VideoUploadRequest(filename="evil.exe", file_size=100)

    def test_upload_request_path_traversal(self):
        """VideoUploadRequest rejects path traversal."""
        from backend.schemas.video import VideoUploadRequest
        with pytest.raises(ValidationError):
            VideoUploadRequest(filename="../escape.mp4", file_size=100)

    def test_upload_request_zero_size(self):
        """VideoUploadRequest rejects zero file size."""
        from backend.schemas.video import VideoUploadRequest
        with pytest.raises(ValidationError):
            VideoUploadRequest(filename="test.mp4", file_size=0)

    def test_video_metadata_valid(self):
        """VideoMetadata accepts valid data."""
        from backend.schemas.video import VideoMetadata
        now = datetime.datetime.now(datetime.timezone.utc)
        vm = VideoMetadata(
            video_id="vid_001",
            filename="test.mp4",
            file_size=100,
            status="uploaded",
            created_at=now,
            updated_at=now,
        )
        assert vm.video_id == "vid_001"

    def test_video_response_valid(self):
        """VideoResponse accepts valid data."""
        from backend.schemas.video import VideoResponse
        now = datetime.datetime.now(datetime.timezone.utc)
        vr = VideoResponse(
            video_id="vid_001",
            filename="test.mp4",
            file_size=100,
            status="uploaded",
            created_at=now,
            updated_at=now,
        )
        assert vr.video_id == "vid_001"


# ===========================================================================
# Analysis Schemas
# ===========================================================================


class TestAnalysisSchemas:
    """Tests for backend.schemas.analysis."""

    def test_detection_schema_valid(self):
        """DetectionSchema accepts valid detection data."""
        from backend.schemas.analysis import DetectionSchema
        now = datetime.datetime.now(datetime.timezone.utc)
        det = DetectionSchema(
            detection_id="det_001",
            video_id="vid_001",
            frame_number=1,
            class_name="person",
            confidence=0.95,
            bbox={"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.8},
            created_at=now,
        )
        assert det.detection_id == "det_001"

    def test_detection_schema_bad_confidence(self):
        """DetectionSchema rejects out-of-range confidence."""
        from backend.schemas.analysis import DetectionSchema
        now = datetime.datetime.now(datetime.timezone.utc)
        with pytest.raises(ValidationError):
            DetectionSchema(
                detection_id="det_002",
                video_id="vid_001",
                frame_number=1,
                class_name="x",
                confidence=1.5,
                bbox={"x": 0, "y": 0, "width": 1, "height": 1},
                created_at=now,
            )

    def test_detection_schema_bad_prefix(self):
        """DetectionSchema rejects wrong detection_id prefix."""
        from backend.schemas.analysis import DetectionSchema
        now = datetime.datetime.now(datetime.timezone.utc)
        with pytest.raises(ValidationError):
            DetectionSchema(
                detection_id="xyz_001",
                video_id="vid_001",
                frame_number=1,
                class_name="x",
                confidence=0.5,
                bbox={"x": 0, "y": 0, "width": 1, "height": 1},
                created_at=now,
            )

    def test_analysis_request_valid(self):
        """AnalysisRequest accepts valid request data."""
        from backend.schemas.analysis import AnalysisRequest
        ar = AnalysisRequest(
            video_id="vid_001",
            detections=[{"class_name": "x", "confidence": 0.9, "bbox": [0, 0, 1, 1]}],
            source_frame=5,
        )
        assert ar.video_id == "vid_001"

    def test_analysis_response_valid(self):
        """AnalysisResponse accepts valid response data."""
        from backend.schemas.analysis import (
            AnalysisResponse, DetectionSchema,
        )
        now = datetime.datetime.now(datetime.timezone.utc)
        det = DetectionSchema(
            detection_id="det_001",
            video_id="vid_001",
            frame_number=1,
            class_name="person",
            confidence=0.95,
            bbox={"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.8},
            created_at=now,
        )
        resp = AnalysisResponse(video_id="vid_001", total_detections=1, detections=[det])
        assert resp.total_detections == 1


# ===========================================================================
# Analytics Schemas
# ===========================================================================


class TestAnalyticsSchemas:
    """Tests for backend.schemas.analytics."""

    def test_analytics_request_valid(self):
        """AnalyticsRequest accepts valid pipeline request."""
        from backend.schemas.analytics import AnalyticsRequest
        ar = AnalyticsRequest(operation="full_pipeline")
        assert ar.operation.value == "full_pipeline"

    def test_analytics_response_valid(self):
        """AnalyticsResponse accepts valid pipeline response."""
        from backend.schemas.analytics import AnalyticsResponse
        resp = AnalyticsResponse(operation="full_pipeline", status="completed")
        assert resp.status == "completed"

    def test_kpi_response_valid(self):
        """KPIResponse accepts valid KPI data."""
        from backend.schemas.analytics import KPIResponse
        now = datetime.datetime.now(datetime.timezone.utc)
        kpi = KPIResponse(metric="total_detections", value=42.0, timestamp=now)
        assert kpi.metric == "total_detections"

    def test_dashboard_metrics_defaults(self):
        """DashboardMetrics has safe defaults."""
        from backend.schemas.analytics import DashboardMetrics
        dm = DashboardMetrics()
        assert dm.freshness_score == 100.0
        assert dm.spoilage_risk_index == 0.0


# ===========================================================================
# Dashboard Schemas
# ===========================================================================


class TestDashboardSchemas:
    """Tests for backend.schemas.dashboard."""

    def test_dashboard_summary_valid(self):
        """DashboardSummary accepts valid summary data."""
        from backend.schemas.dashboard import DashboardSummary
        ds = DashboardSummary(
            total_videos=10,
            total_detections=500,
            total_events=25,
            total_alerts=5,
            total_kpis=12,
        )
        assert ds.total_videos == 10

    def test_dashboard_statistics_valid(self):
        """DashboardStatistics accepts valid stats data."""
        from backend.schemas.dashboard import DashboardStatistics
        ds = DashboardStatistics(
            total_detections=100,
            unique_classes=5,
            average_confidence=0.85,
        )
        assert ds.unique_classes == 5


# ===========================================================================
# Report Schemas
# ===========================================================================


class TestReportSchemas:
    """Tests for backend.schemas.report."""

    def test_report_request_valid(self):
        """ReportRequest accepts valid request data."""
        from backend.schemas.report import ReportRequest
        rr = ReportRequest(format="pdf")
        assert rr.format.value == "pdf"

    def test_report_response_valid(self):
        """ReportResponse accepts valid response data."""
        from backend.schemas.report import ReportResponse
        now = datetime.datetime.now(datetime.timezone.utc)
        resp = ReportResponse(
            report_id="rpt_001",
            format="pdf",
            status="generated",
            file_path="/tmp/report.pdf",
            generated_at=now,
        )
        assert resp.report_id == "rpt_001"


# ===========================================================================
# Settings Schemas
# ===========================================================================


class TestSettingsSchemas:
    """Tests for backend.schemas.settings."""

    def test_settings_response_valid(self):
        """SettingsResponse accepts valid settings data."""
        from backend.schemas.settings import SettingsResponse
        sr = SettingsResponse(
            project_name="VisionOps AI",
            version="1.0.0",
            environment="development",
        )
        assert sr.project_name == "VisionOps AI"

    def test_settings_update_partial(self):
        """SettingsUpdate accepts partial updates."""
        from backend.schemas.settings import SettingsUpdate
        su = SettingsUpdate(confidence_threshold=0.6)
        assert su.confidence_threshold == 0.6


# ===========================================================================
# Package Import
# ===========================================================================


class TestPackageImport:
    """Tests for the ``backend.schemas`` package re-export."""

    def test_package_importable(self):
        """The schemas package is importable."""
        import backend.schemas  # noqa: F401

    def test_package_has_all(self):
        """The schemas package has __all__ defined."""
        import backend.schemas
        assert len(backend.schemas.__all__) > 0

    def test_package_re_exports(self):
        """Key schemas are re-exported from the package."""
        import backend.schemas as schemas
        assert schemas.LoginRequest is not None
        assert schemas.VideoUploadRequest is not None
        assert schemas.AnalysisRequest is not None
        assert schemas.AnalyticsRequest is not None
        assert schemas.DashboardSummary is not None
        assert schemas.ReportRequest is not None
        assert schemas.SettingsResponse is not None

