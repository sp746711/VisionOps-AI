"""VisionOps AI — Unit tests for the ``analytics`` package.

Tests:
- AnalyticsService: pipeline, KPIs, spoilage metrics, freshness metrics
- Dashboard data preparation
- Import tests for all analytics modules
- Edge cases and failure modes
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, AsyncMock

import pytest

from backend.exceptions import AnalyticsError, ValidationError


# ===========================================================================
# Analytics Module Imports
# ===========================================================================


class TestAnalyticsImports:
    """Verify that all analytics modules are importable."""

    def test_analytics_init(self):
        """The analytics __init__ module can be imported."""
        import backend.analytics  # noqa: F401

    def test_aggregator(self):
        """The aggregator module can be imported."""
        import backend.analytics.aggregator  # noqa: F401

    def test_cleaner(self):
        """The cleaner module can be imported."""
        import backend.analytics.cleaner  # noqa: F401

    def test_dashboard_dataset(self):
        """The dashboard_dataset module can be imported."""
        import backend.analytics.dashboard_dataset  # noqa: F401

    def test_loader(self):
        """The loader module can be imported."""
        import backend.analytics.loader  # noqa: F401

    def test_pipeline(self):
        """The pipeline module can be imported."""
        import backend.analytics.pipeline  # noqa: F401

    def test_powerbi_dataset(self):
        """The powerbi_dataset module can be imported."""
        import backend.analytics.powerbi_dataset  # noqa: F401

    def test_report_generator(self):
        """The report_generator module can be imported."""
        import backend.analytics.report_generator  # noqa: F401

    def test_transformer(self):
        """The transformer module can be imported."""
        import backend.analytics.transformer  # noqa: F401


# ===========================================================================
# Analytics Schemas
# ===========================================================================


class TestAnalyticsSchemas:
    """Tests for analytics-related Pydantic schemas."""

    def test_analytics_request_schema(self):
        """AnalyticsRequest schema exists."""
        from backend.schemas.analytics import AnalyticsRequest
        assert AnalyticsRequest is not None

    def test_analytics_response_schema(self):
        """AnalyticsResponse schema exists."""
        from backend.schemas.analytics import AnalyticsResponse
        assert AnalyticsResponse is not None


# ===========================================================================
# AnalyticsService — Pipeline
# ===========================================================================


class TestAnalyticsServicePipeline:
    """Tests for AnalyticsService pipeline execution."""

    @pytest.mark.asyncio
    async def test_run_pipeline_full(self, mock_storage_with_csv_data: MagicMock):
        """run_pipeline executes full_pipeline operation."""
        from backend.services.analytics_service import AnalyticsService

        service = AnalyticsService(storage=mock_storage_with_csv_data)
        result = await service.run_pipeline(operation="full_pipeline")
        assert result["operation"] == "full_pipeline"
        assert result["status"] == "completed"
        assert "aggregation" in result
        assert "kpis" in result

    @pytest.mark.asyncio
    async def test_run_pipeline_aggregation_only(self, mock_storage_with_csv_data: MagicMock):
        """run_pipeline executes aggregation_only operation."""
        from backend.services.analytics_service import AnalyticsService

        service = AnalyticsService(storage=mock_storage_with_csv_data)
        result = await service.run_pipeline(operation="aggregation_only")
        assert result["operation"] == "aggregation_only"
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_pipeline_kpi_only(self, mock_storage_with_csv_data: MagicMock):
        """run_pipeline executes kpi_only operation."""
        from backend.services.analytics_service import AnalyticsService

        service = AnalyticsService(storage=mock_storage_with_csv_data)
        result = await service.run_pipeline(operation="kpi_only")
        assert result["operation"] == "kpi_only"
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_pipeline_invalid_operation(self, mock_storage_service: MagicMock):
        """run_pipeline raises ValidationError for invalid operation."""
        from backend.services.analytics_service import AnalyticsService

        service = AnalyticsService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="Invalid operation"):
            await service.run_pipeline(operation="invalid_op")

    @pytest.mark.asyncio
    async def test_run_pipeline_empty_data(self, mock_storage_service: MagicMock):
        """run_pipeline handles empty data gracefully."""
        from backend.services.analytics_service import AnalyticsService

        mock_storage_service.read_csv_store.return_value = []
        service = AnalyticsService(storage=mock_storage_service)
        result = await service.run_pipeline(operation="full_pipeline")
        assert result["status"] == "completed"


# ===========================================================================
# AnalyticsService — KPIs
# ===========================================================================


class TestAnalyticsServiceKPIs:
    """Tests for AnalyticsService KPI calculations."""

    def test_calculate_kpis(self, mock_storage_with_csv_data: MagicMock):
        """calculate_kpis returns KPI records."""
        from backend.services.analytics_service import AnalyticsService

        service = AnalyticsService(storage=mock_storage_with_csv_data)
        kpis = service.calculate_kpis()
        assert len(kpis) > 0
        assert any(k["metric"] == "total_detections" for k in kpis)

    def test_calculate_kpis_invalid_limit(self, mock_storage_service: MagicMock):
        """calculate_kpis raises ValidationError for invalid limit."""
        from backend.services.analytics_service import AnalyticsService

        service = AnalyticsService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="limit must be between"):
            service.calculate_kpis(limit=0)

    def test_calculate_kpis_specific_metrics(self, mock_storage_with_csv_data: MagicMock):
        """calculate_kpis returns specific metrics when requested."""
        from backend.services.analytics_service import AnalyticsService

        service = AnalyticsService(storage=mock_storage_with_csv_data)
        kpis = service.calculate_kpis(metrics=["total_detections"])
        assert len(kpis) >= 1


# ===========================================================================
# AnalyticsService — Spoilage Metrics
# ===========================================================================


class TestAnalyticsServiceSpoilageMetrics:
    """Tests for AnalyticsService spoilage metrics."""

    def test_compute_spoilage_metrics(self, mock_storage_with_csv_data: MagicMock):
        """compute_spoilage_metrics returns spoilage risk data."""
        from backend.services.analytics_service import AnalyticsService

        service = AnalyticsService(storage=mock_storage_with_csv_data)
        metrics = service.compute_spoilage_metrics()
        assert "spoilage_risk_index" in metrics
        assert "high_risk_detections" in metrics
        assert "risk_factors" in metrics

    def test_compute_spoilage_metrics_empty_data(self, mock_storage_service: MagicMock):
        """compute_spoilage_metrics returns safe defaults for empty data."""
        from backend.services.analytics_service import AnalyticsService

        mock_storage_service.read_csv_store.return_value = []
        service = AnalyticsService(storage=mock_storage_service)
        metrics = service.compute_spoilage_metrics()
        assert metrics["spoilage_risk_index"] == 0.0

    def test_compute_spoilage_metrics_high_risk(self, mock_storage_service: MagicMock):
        """compute_spoilage_metrics detects high risk scenarios."""
        from backend.services.analytics_service import AnalyticsService

        mock_storage_service.read_csv_store.return_value = [
            {"class_name": "spoiled_food", "confidence": "0.95"},
        ]
        service = AnalyticsService(storage=mock_storage_service)
        metrics = service.compute_spoilage_metrics()
        assert metrics["high_risk_detections"] > 0


# ===========================================================================
# AnalyticsService — Freshness Metrics
# ===========================================================================


class TestAnalyticsServiceFreshnessMetrics:
    """Tests for AnalyticsService freshness metrics."""

    def test_compute_freshness_metrics(self, mock_storage_with_csv_data: MagicMock):
        """compute_freshness_metrics returns freshness data."""
        from backend.services.analytics_service import AnalyticsService

        service = AnalyticsService(storage=mock_storage_with_csv_data)
        metrics = service.compute_freshness_metrics()
        assert "freshness_score" in metrics
        assert "turnover_rate" in metrics
        assert "stale_detection_ratio" in metrics

    def test_compute_freshness_metrics_empty(self, mock_storage_service: MagicMock):
        """compute_freshness_metrics returns safe defaults for empty data."""
        from backend.services.analytics_service import AnalyticsService

        mock_storage_service.read_csv_store.return_value = []
        service = AnalyticsService(storage=mock_storage_service)
        metrics = service.compute_freshness_metrics()
        assert metrics["freshness_score"] == 100.0


# ===========================================================================
# AnalyticsService — Dashboard Data
# ===========================================================================


class TestAnalyticsServiceDashboardData:
    """Tests for AnalyticsService dashboard data preparation."""

    def test_prepare_dashboard_data(self, mock_storage_with_csv_data: MagicMock):
        """prepare_dashboard_data returns dashboard-ready data."""
        from backend.services.analytics_service import AnalyticsService

        service = AnalyticsService(storage=mock_storage_with_csv_data)
        data = service.prepare_dashboard_data()
        assert "summary" in data
        assert "detection_trends" in data
        assert "alert_summary" in data
        assert "top_classes" in data
        assert "recent_events" in data

    def test_prepare_dashboard_data_empty(self, mock_storage_service: MagicMock):
        """prepare_dashboard_data returns safe defaults for empty data."""
        from backend.services.analytics_service import AnalyticsService

        mock_storage_service.read_csv_store.return_value = []
        service = AnalyticsService(storage=mock_storage_service)
        data = service.prepare_dashboard_data()
        assert data["summary"]["total_detections"] == 0


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestAnalyticsEdgeCases:
    """Edge-case tests for analytics."""

    def test_large_confidence_values(self, mock_storage_service: MagicMock):
        """compute_spoilage_metrics handles extreme confidence values."""
        from backend.services.analytics_service import AnalyticsService

        mock_storage_service.read_csv_store.return_value = [
            {"class_name": "item", "confidence": "999.0"},
            {"class_name": "item", "confidence": "-1.0"},
        ]
        service = AnalyticsService(storage=mock_storage_service)
        metrics = service.compute_spoilage_metrics()
        assert isinstance(metrics["spoilage_risk_index"], float)

    def test_missing_confidence_field(self, mock_storage_service: MagicMock):
        """compute_spoilage_metrics handles missing confidence field."""
        from backend.services.analytics_service import AnalyticsService

        mock_storage_service.read_csv_store.return_value = [
            {"class_name": "item"},
        ]
        service = AnalyticsService(storage=mock_storage_service)
        metrics = service.compute_spoilage_metrics()
        assert isinstance(metrics["spoilage_risk_index"], float)
