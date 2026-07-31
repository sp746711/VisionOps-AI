"""VisionOps AI — Unit tests for the ``reports`` API module and ReportService.

Tests:
- Report API endpoint schemas
- ReportService: PDF, CSV, JSON generation
- Empty report, large report, export validation
- Edge cases and failure modes
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from backend.exceptions import ValidationError


# ===========================================================================
# Reports API Module
# ===========================================================================


class TestReportsAPIImports:
    """Verify reports-related modules are importable."""

    def test_reports_api_module(self):
        """The reports API module can be imported."""
        import backend.api.reports  # noqa: F401

    def test_reports_schemas_module(self):
        """The report schema module can be imported."""
        import backend.schemas.report  # noqa: F401

    def test_reports_service_module(self):
        """The report_service module can be imported."""
        import backend.services.report_service  # noqa: F401

    def test_reports_model_module(self):
        """The report model module can be imported."""
        import backend.models.report  # noqa: F401


# ===========================================================================
# Report Schemas
# ===========================================================================


class TestReportSchemas:
    """Tests for report-related Pydantic schemas."""

    def test_report_request_schema(self):
        """ReportRequest schema exists."""
        from backend.schemas.report import ReportRequest
        assert ReportRequest is not None

    def test_report_response_schema(self):
        """ReportResponse schema exists."""
        from backend.schemas.report import ReportResponse
        assert ReportResponse is not None


# ===========================================================================
# ReportService — PDF Generation
# ===========================================================================


class TestReportServicePDF:
    """Tests for ReportService PDF generation."""

    @pytest.mark.asyncio
    async def test_generate_pdf(self, mock_storage_with_csv_data: MagicMock):
        """generate_report creates a PDF report."""
        from backend.services.report_service import ReportService

        mock_storage_with_csv_data.file_manager.save_report_file.return_value = \
            Path("/tmp/reports/rpt_001.pdf")
        service = ReportService(storage=mock_storage_with_csv_data)

        result = await service.generate_report(format="pdf")
        assert result["format"] == "pdf"
        assert "report_id" in result
        assert result["report_id"].startswith("rpt_")
        assert "file_path" in result
        assert result["status"] == "generated"

    @pytest.mark.asyncio
    async def test_generate_pdf_convenience(self, mock_storage_with_csv_data: MagicMock):
        """generate_pdf is a convenience wrapper."""
        from backend.services.report_service import ReportService

        mock_storage_with_csv_data.file_manager.save_report_file.return_value = \
            Path("/tmp/reports/rpt_001.pdf")
        service = ReportService(storage=mock_storage_with_csv_data)

        result = await service.generate_pdf()
        assert result["format"] == "pdf"


# ===========================================================================
# ReportService — Excel Generation
# ===========================================================================


class TestReportServiceExcel:
    """Tests for ReportService Excel generation."""

    @pytest.mark.asyncio
    async def test_generate_excel(self, mock_storage_with_csv_data: MagicMock):
        """generate_excel is a convenience wrapper for Excel reports."""
        from backend.services.report_service import ReportService

        mock_storage_with_csv_data.file_manager.save_report_file.return_value = \
            Path("/tmp/reports/rpt_001.xlsx")
        service = ReportService(storage=mock_storage_with_csv_data)

        result = await service.generate_excel()
        assert result["format"] == "excel"

    @pytest.mark.asyncio
    async def test_generate_excel_with_report_type(self, mock_storage_with_csv_data: MagicMock):
        """generate_report with format=excel creates Excel report."""
        from backend.services.report_service import ReportService

        mock_storage_with_csv_data.file_manager.save_report_file.return_value = \
            Path("/tmp/reports/rpt_001.xlsx")
        service = ReportService(storage=mock_storage_with_csv_data)

        result = await service.generate_report(format="excel")
        assert result["format"] == "excel"


# ===========================================================================
# ReportService — JSON Generation
# ===========================================================================


class TestReportServiceJSON:
    """Tests for ReportService JSON generation."""

    @pytest.mark.asyncio
    async def test_generate_json_report(self, mock_storage_with_csv_data: MagicMock):
        """generate_json_report is a convenience wrapper for JSON reports."""
        from backend.services.report_service import ReportService

        mock_storage_with_csv_data.file_manager.save_report_file.return_value = \
            Path("/tmp/reports/rpt_001.json")
        service = ReportService(storage=mock_storage_with_csv_data)

        result = await service.generate_json_report()
        assert result["format"] == "json"

    @pytest.mark.asyncio
    async def test_generate_json_with_report_type(self, mock_storage_with_csv_data: MagicMock):
        """generate_report with format=json creates JSON report."""
        from backend.services.report_service import ReportService

        mock_storage_with_csv_data.file_manager.save_report_file.return_value = \
            Path("/tmp/reports/rpt_001.json")
        service = ReportService(storage=mock_storage_with_csv_data)

        result = await service.generate_report(format="json")
        assert result["format"] == "json"


# ===========================================================================
# ReportService — Error Handling
# ===========================================================================


class TestReportServiceErrors:
    """Tests for ReportService error handling."""

    @pytest.mark.asyncio
    async def test_generate_report_invalid_format(self, mock_storage_service: MagicMock):
        """generate_report raises ValidationError for invalid format."""
        from backend.services.report_service import ReportService

        service = ReportService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="Invalid report format"):
            await service.generate_report(format="docx")

    @pytest.mark.asyncio
    async def test_generate_report_empty_format(self, mock_storage_service: MagicMock):
        """generate_report raises ValidationError for empty format."""
        from backend.services.report_service import ReportService

        service = ReportService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="Report format must not be empty"):
            await service.generate_report(format="")

    @pytest.mark.asyncio
    async def test_generate_report_storage_error(self, mock_storage_service: MagicMock):
        """generate_report handles storage service errors."""
        from backend.services.report_service import ReportService

        mock_storage_service.csv_manager.read_store.side_effect = Exception("Storage error")
        service = ReportService(storage=mock_storage_service)

        with pytest.raises(Exception, match="Failed to generate report"):
            await service.generate_report(format="pdf")


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestReportEdgeCases:
    """Edge-case tests for reports."""

    def test_report_id_format(self):
        """report_id follows expected format."""
        from backend.services.report_service import ReportService

        service = ReportService()
        report_id = service._generate_report_id()
        assert report_id.startswith("rpt_")
        assert len(report_id) > 4

    @pytest.mark.asyncio
    async def test_generate_report_empty_data(self, mock_storage_service: MagicMock):
        """generate_report handles empty data gracefully."""
        from backend.services.report_service import ReportService

        mock_storage_service.read_csv_store.return_value = []
        mock_storage_service.file_manager.save_report_file.return_value = \
            Path("/tmp/reports/rpt_001.pdf")
        service = ReportService(storage=mock_storage_service)

        result = await service.generate_report(format="pdf")
        assert result["status"] == "generated"

    def test_available_formats(self):
        """available_formats returns supported formats."""
        from backend.services.report_service import ReportService

        service = ReportService()
        formats = service.available_formats
        assert "pdf" in formats
        assert "excel" in formats
        assert "json" in formats
