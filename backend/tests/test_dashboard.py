"""VisionOps AI — Unit tests for the ``dashboard`` API module and DashboardService.

Tests:
- Dashboard API endpoint schemas
- DashboardService: summary, detection stats, alert summary, performance metrics
- Edge cases and failure modes
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.exceptions import ValidationError


# ===========================================================================
# Dashboard API Module
# ===========================================================================


class TestDashboardAPIImports:
    """Verify dashboard-related modules are importable."""

    def test_dashboard_api_module(self):
        """The dashboard API module can be imported."""
        import backend.api.dashboard  # noqa: F401

    def test_dashboard_schemas_module(self):
        """The dashboard schema module can be imported."""
        import backend.schemas.dashboard  # noqa: F401

    def test_dashboard_service_module(self):
        """The dashboard_service module can be imported."""
        import backend.services.dashboard_service  # noqa: F401

    def test_dashboard_model_module(self):
        """The dashboard model module can be imported."""
        import backend.models.kpi  # noqa: F401


# ===========================================================================
# Dashboard Schemas
# ===========================================================================


class TestDashboardSchemas:
    """Tests for dashboard-related Pydantic schemas."""

    def test_dashboard_summary_schema(self):
        """DashboardSummary schema exists."""
        from backend.schemas.dashboard import DashboardSummary
        assert DashboardSummary is not None

    def test_dashboard_stats_schema(self):
        """DashboardStats schema exists."""
        from backend.schemas.dashboard import DashboardStats
        assert DashboardStats is not None


# ===========================================================================
# DashboardService — Summary
# ===========================================================================


class TestDashboardServiceSummary:
    """Tests for DashboardService summary methods."""

    def test_get_summary(self, mock_storage_with_csv_data: MagicMock):
        """get_summary returns overall dashboard counts."""
        from backend.services.dashboard_service import DashboardService

        service = DashboardService(storage=mock_storage_with_csv_data)
        summary = service.get_summary()
        assert "total_videos" in summary
        assert "total_detections" in summary
        assert "total_events" in summary
        assert "total_alerts" in summary
        assert "total_kpis" in summary
        assert "videos_by_status" in summary

    def test_get_summary_detection_count(self, mock_storage_with_csv_data: MagicMock):
        """get_summary returns correct detection count."""
        from backend.services.dashboard_service import DashboardService

        service = DashboardService(storage=mock_storage_with_csv_data)
        summary = service.get_summary()
        assert summary["total_detections"] > 0

    def test_get_summary_alert_count(self, mock_storage_with_csv_data: MagicMock):
        """get_summary returns correct alert count."""
        from backend.services.dashboard_service import DashboardService

        service = DashboardService(storage=mock_storage_with_csv_data)
        summary = service.get_summary()
        assert summary["total_alerts"] > 0

    def test_get_summary_empty_data(self, mock_storage_service: MagicMock):
        """get_summary returns zero counts for empty data."""
        from backend.services.dashboard_service import DashboardService

        mock_storage_service.read_csv_store.return_value = []
        service = DashboardService(storage=mock_storage_service)
        summary = service.get_summary()
        assert summary["total_videos"] == 0
        assert summary["total_detections"] == 0


# ===========================================================================
# DashboardService — Detection Stats
# ===========================================================================


class TestDashboardServiceDetectionStats:
    """Tests for DashboardService detection statistics."""

    def test_get_detection_stats(self, mock_storage_with_csv_data: MagicMock):
        """get_detection_stats returns detection statistics."""
        from backend.services.dashboard_service import DashboardService

        service = DashboardService(storage=mock_storage_with_csv_data)
        stats = service.get_detection_stats()
        assert "total_detections" in stats
        assert "unique_classes" in stats
        assert "average_confidence" in stats
        assert "top_classes" in stats
        assert "confidence_distribution" in stats
        assert "detections_over_time" in stats

    def test_get_detection_stats_invalid_limit(self, mock_storage_service: MagicMock):
        """get_detection_stats raises ValidationError for invalid limit."""
        from backend.services.dashboard_service import DashboardService

        service = DashboardService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="limit must be between"):
            service.get_detection_stats(limit=0)

    def test_get_detection_stats_empty(self, mock_storage_service: MagicMock):
        """get_detection_stats returns empty stats for no data."""
        from backend.services.dashboard_service import DashboardService

        mock_storage_service.read_csv_store.return_value = []
        service = DashboardService(storage=mock_storage_service)
        stats = service.get_detection_stats()
        assert stats["total_detections"] == 0
        assert stats["unique_classes"] == 0

    def test_get_detection_stats_top_classes(self, mock_storage_with_csv_data: MagicMock):
        """get_detection_stats returns ranked top classes."""
        from backend.services.dashboard_service import DashboardService

        service = DashboardService(storage=mock_storage_with_csv_data)
        stats = service.get_detection_stats(limit=5)
        assert len(stats["top_classes"]) <= 5


# ===========================================================================
# DashboardService — Alert Summary
# ===========================================================================


class TestDashboardServiceAlertSummary:
    """Tests for DashboardService alert summary."""

    def test_get_alert_summary(self, mock_storage_with_csv_data: MagicMock):
        """get_alert_summary returns alert summary data."""
        from backend.services.dashboard_service import DashboardService

        service = DashboardService(storage=mock_storage_with_csv_data)
        summary = service.get_alert_summary()
        assert "total_alerts" in summary
        assert "by_severity" in summary
        assert "recent_alerts" in summary

    def test_get_alert_summary_by_severity(self, mock_storage_with_csv_data: MagicMock):
        """get_alert_summary groups by severity correctly."""
        from backend.services.dashboard_service import DashboardService

        service = DashboardService(storage=mock_storage_with_csv_data)
        summary = service.get_alert_summary()
        assert "high" in summary["by_severity"]
        assert "medium" in summary["by_severity"]

    def test_get_alert_summary_invalid_severity(self, mock_storage_service: MagicMock):
        """get_alert_summary raises ValidationError for invalid severity."""
        from backend.services.dashboard_service import DashboardService

        service = DashboardService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="Invalid min_severity"):
            service.get_alert_summary(min_severity="invalid")

    def test_get_alert_summary_empty(self, mock_storage_service: MagicMock):
        """get_alert_summary returns zero counts for empty data."""
        from backend.services.dashboard_service import DashboardService

        mock_storage_service.read_csv_store.return_value = []
        service = DashboardService(storage=mock_storage_service)
        alert_summary = service.get_alert_summary()
        assert alert_summary["total_alerts"] == 0


# ===========================================================================
# DashboardService — Performance Metrics
# ===========================================================================


class TestDashboardServicePerformanceMetrics:
    """Tests for DashboardService performance metrics."""

    def test_get_performance_metrics(self, mock_storage_with_csv_data: MagicMock):
        """get_performance_metrics returns performance data."""
        from backend.services.dashboard_service import DashboardService

        service = DashboardService(storage=mock_storage_with_csv_data)
        metrics = service.get_performance_metrics(days=7)
        assert "period_days" in metrics
        assert "videos_processed" in metrics
        assert "processing_success_rate" in metrics
        assert "average_processing_time" in metrics

    def test_get_performance_metrics_invalid_days(self, mock_storage_service: MagicMock):
        """get_performance_metrics raises ValidationError for invalid days."""
        from backend.services.dashboard_service import DashboardService

        service = DashboardService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="days must be between"):
            service.get_performance_metrics(days=0)

    def test_get_performance_metrics_empty(self, mock_storage_service: MagicMock):
        """get_performance_metrics returns defaults for empty data."""
        from backend.services.dashboard_service import DashboardService

        mock_storage_service.read_csv_store.return_value = []
        service = DashboardService(storage=mock_storage_service)
        metrics = service.get_performance_metrics(days=7)
        assert metrics["videos_processed"] == 0
        assert metrics["processing_success_rate"] == 0.0


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestDashboardEdgeCases:
    """Edge-case tests for the dashboard layer."""

    def test_none_values_in_data(self, mock_storage_service: MagicMock):
        """get_summary handles None values in data."""
        from backend.services.dashboard_service import DashboardService

        mock_storage_service.read_csv_store.return_value = [
            {"video_id": "vid_001", "status": None},
        ]
        service = DashboardService(storage=mock_storage_service)
        summary = service.get_summary()
        assert isinstance(summary["total_videos"], int)
