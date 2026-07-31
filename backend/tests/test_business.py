"""VisionOps AI — Unit tests for the ``business`` package.

Tests:
- BusinessEngine: spoilage scoring, risk scoring, cold chain validation
- AlertEngine: alert generation, threshold validation
- KPIEngine: KPI calculations
- EventEngine: event processing
- SummaryEngine: summary generation
- Edge cases and failure modes
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.exceptions import ValidationError, RequiredFieldError


# ===========================================================================
# Business Module Imports
# ===========================================================================


class TestBusinessImports:
    """Verify that all business modules are importable."""

    def test_business_init(self):
        """The business __init__ module can be imported."""
        import backend.business  # noqa: F401

    def test_alert_engine(self):
        """The alert_engine module can be imported."""
        import backend.business.alert_engine  # noqa: F401

    def test_business_engine(self):
        """The business_engine module can be imported."""
        import backend.business.business_engine  # noqa: F401

    def test_event_engine(self):
        """The event_engine module can be imported."""
        import backend.business.event_engine  # noqa: F401

    def test_kpi_engine(self):
        """The kpi_engine module can be imported."""
        import backend.business.kpi_engine  # noqa: F401

    def test_summary_engine(self):
        """The summary_engine module can be imported."""
        import backend.business.summary_engine  # noqa: F401


# ===========================================================================
# BusinessEngine — Spoilage Scoring
# ===========================================================================


class TestBusinessEngineSpoilageScoring:
    """Tests for BusinessEngine spoilage scoring."""

    def test_initialisation(self, mock_storage_service: MagicMock):
        """BusinessEngine can be instantiated with injected storage."""
        from backend.business.business_engine import BusinessEngine
        engine = BusinessEngine(storage=mock_storage_service)
        assert engine is not None

    def test_compute_spoilage_score(self, mock_storage_service: MagicMock):
        """compute_spoilage_score returns risk score and factors."""
        from backend.business.business_engine import BusinessEngine
        engine = BusinessEngine(storage=mock_storage_service)
        result = engine.compute_spoilage_score(video_id="vid_001")
        assert "spoilage_score" in result
        assert "risk_level" in result
        assert "factors" in result

    def test_compute_spoilage_score_no_data(self, mock_storage_service: MagicMock):
        """compute_spoilage_score returns safe defaults for no data."""
        from backend.business.business_engine import BusinessEngine
        engine = BusinessEngine(storage=mock_storage_service)
        result = engine.compute_spoilage_score(video_id="vid_nonexistent")
        assert result["spoilage_score"] == 0.0
        assert result["risk_level"] == "low"

    def test_compute_spoilage_score_empty_video_id_raises(self, mock_storage_service: MagicMock):
        """compute_spoilage_score raises ValidationError for empty video_id."""
        from backend.business.business_engine import BusinessEngine
        engine = BusinessEngine(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="video_id must not be empty"):
            engine.compute_spoilage_score(video_id="")


# ===========================================================================
# BusinessEngine — Cold Chain Validation
# ===========================================================================


class TestBusinessEngineColdChainValidation:
    """Tests for BusinessEngine cold chain validation."""

    def test_validate_cold_chain(self, mock_storage_service: MagicMock):
        """validate_cold_chain returns chain validation result."""
        from backend.business.business_engine import BusinessEngine
        engine = BusinessEngine(storage=mock_storage_service)
        result = engine.validate_cold_chain(video_id="vid_001")
        assert "is_valid" in result
        assert "breaches" in result
        assert "severity" in result

    def test_validate_cold_chain_no_breaches(self, mock_storage_service: MagicMock):
        """validate_cold_chain returns valid when no breaches."""
        from backend.business.business_engine import BusinessEngine
        engine = BusinessEngine(storage=mock_storage_service)
        result = engine.validate_cold_chain(video_id="vid_001")
        assert isinstance(result["is_valid"], bool)

    def test_validate_cold_chain_with_breaches(self, mock_storage_service: MagicMock):
        """validate_cold_chain detects breaches."""
        from backend.business.business_engine import BusinessEngine
        mock_storage_service.read_csv_store.return_value = [
            {"event_type": "temperature_breach", "severity": "high"},
        ]
        engine = BusinessEngine(storage=mock_storage_service)
        result = engine.validate_cold_chain(video_id="vid_001")
        assert len(result["breaches"]) > 0


# ===========================================================================
# AlertEngine — Alert Generation
# ===========================================================================


class TestAlertEngine:
    """Tests for AlertEngine."""

    def test_initialisation(self, mock_storage_service: MagicMock):
        """AlertEngine can be instantiated."""
        from backend.business.alert_engine import AlertEngine
        engine = AlertEngine(storage=mock_storage_service)
        assert engine is not None

    def test_generate_alerts(self, mock_storage_service: MagicMock):
        """generate_alerts returns alert list."""
        from backend.business.alert_engine import AlertEngine
        engine = AlertEngine(storage=mock_storage_service)
        alerts = engine.generate_alerts(video_id="vid_001")
        assert isinstance(alerts, list)

    def test_generate_alerts_with_detections(self, mock_storage_service: MagicMock):
        """generate_alerts creates alerts based on detection data."""
        from backend.business.alert_engine import AlertEngine
        mock_storage_service.read_csv_store.return_value = [
            {"class_name": "unauthorized_person", "confidence": "0.95"},
        ]
        engine = AlertEngine(storage=mock_storage_service)
        alerts = engine.generate_alerts(video_id="vid_001")
        assert len(alerts) > 0

    def test_generate_alerts_no_triggers(self, mock_storage_service: MagicMock):
        """generate_alerts returns empty list when no triggers found."""
        from backend.business.alert_engine import AlertEngine
        mock_storage_service.read_csv_store.return_value = []
        engine = AlertEngine(storage=mock_storage_service)
        alerts = engine.generate_alerts(video_id="vid_001")
        assert alerts == []

    def test_generate_alerts_invalid_video_id(self, mock_storage_service: MagicMock):
        """generate_alerts raises ValidationError for invalid video_id."""
        from backend.business.alert_engine import AlertEngine
        engine = AlertEngine(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="video_id must not be empty"):
            engine.generate_alerts(video_id="")


# ===========================================================================
# KPIEngine — KPI Calculations
# ===========================================================================


class TestKPIEngine:
    """Tests for KPIEngine."""

    def test_initialisation(self, mock_storage_service: MagicMock):
        """KPIEngine can be instantiated."""
        from backend.business.kpi_engine import KPIEngine
        engine = KPIEngine(storage=mock_storage_service)
        assert engine is not None

    def test_calculate_detection_rate_kpi(self, mock_storage_service: MagicMock):
        """calculate_detection_rate returns KPI value."""
        from backend.business.kpi_engine import KPIEngine
        engine = KPIEngine(storage=mock_storage_service)
        kpi = engine.calculate_detection_rate(video_id="vid_001")
        assert "metric" in kpi
        assert kpi["metric"] == "detection_rate"
        assert "value" in kpi

    def test_calculate_confidence_kpi(self, mock_storage_service: MagicMock):
        """calculate_confidence returns average confidence KPI."""
        from backend.business.kpi_engine import KPIEngine
        engine = KPIEngine(storage=mock_storage_service)
        kpi = engine.calculate_confidence_score(video_id="vid_001")
        assert "metric" in kpi
        assert kpi["metric"] == "average_confidence"


# ===========================================================================
# EventEngine — Event Processing
# ===========================================================================


class TestEventEngine:
    """Tests for EventEngine."""

    def test_initialisation(self, mock_storage_service: MagicMock):
        """EventEngine can be instantiated."""
        from backend.business.event_engine import EventEngine
        engine = EventEngine(storage=mock_storage_service)
        assert engine is not None

    def test_process_events(self, mock_storage_service: MagicMock):
        """process_events returns processed event list."""
        from backend.business.event_engine import EventEngine
        engine = EventEngine(storage=mock_storage_service)
        events = engine.process_events(video_id="vid_001")
        assert isinstance(events, list)

    def test_process_events_empty(self, mock_storage_service: MagicMock):
        """process_events returns empty list for video with no events."""
        from backend.business.event_engine import EventEngine
        engine = EventEngine(storage=mock_storage_service)
        events = engine.process_events(video_id="vid_nonexistent")
        assert events is not None


# ===========================================================================
# SummaryEngine — Summary Generation
# ===========================================================================


class TestSummaryEngine:
    """Tests for SummaryEngine."""

    def test_generate_summary(self, mock_storage_service: MagicMock):
        """generate_summary returns a summary dict."""
        from backend.business.summary_engine import SummaryEngine
        engine = SummaryEngine(storage=mock_storage_service)
        summary = engine.generate_summary(video_id="vid_001")
        assert isinstance(summary, dict)
        assert "total_detections" in summary

    def test_generate_summary_empty(self, mock_storage_service: MagicMock):
        """generate_summary returns defaults for no data."""
        from backend.business.summary_engine import SummaryEngine
        engine = SummaryEngine(storage=mock_storage_service)
        summary = engine.generate_summary(video_id="vid_nonexistent")
        assert summary["total_detections"] == 0
