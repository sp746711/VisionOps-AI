"""VisionOps AI — Report Service.

Provides business-logic orchestration for report generation across
multiple formats (PDF, Excel, JSON). Delegates report content
preparation to ``backend.analytics`` and ``backend.business``, and
file output to the storage layer.

Responsibilities:
    - Report orchestration across formats
    - PDF request preparation
    - Excel request preparation
    - JSON report generation
    - Report metadata tracking

Usage::

    from backend.services import ReportService

    service = ReportService()
    pdf = await service.generate_pdf(filters={...})
    excel = await service.generate_excel(filters={...})
    json_report = await service.generate_json_report(filters={...})
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.exceptions import (
    ValidationError,
    StorageError,
    RequiredFieldError,
)
from backend.storage import StorageService
from backend.utils.date_utils import now_utc
from backend.utils.id_generator import generate_report_id

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_FORMATS: frozenset[str] = frozenset({"pdf", "excel", "csv", "json"})
_REPORT_ID_PREFIX: str = "rpt_"

# ---------------------------------------------------------------------------
# ReportService
# ---------------------------------------------------------------------------


class ReportService:
    """Orchestrates report generation across PDF, Excel, CSV, and JSON
    formats.

    This service sits between the API layer and the storage/analytics
    layers. It coordinates report data preparation, format-specific
    rendering, and output persistence — without implementing any
    low-level PDF, Excel, or CSV generation logic.

    Dependency injection is used for the storage layer to improve
    testability.

    Raises:
        ValidationError: If input arguments are invalid.
        StorageError: If storage operations fail.
        ReportError: If report generation fails.
    """

    def __init__(
        self,
        storage: StorageService | None = None,
    ) -> None:
        """Initialise the report service.

        Args:
            storage: Injected ``StorageService`` instance. When ``None``,
                a default instance is created.
        """
        self._storage = storage or StorageService()
        logger.info(
            "ReportService initialised (storage=%s)",
            type(self._storage).__name__,
        )

    # ------------------------------------------------------------------
    # Report Orchestration
    # ------------------------------------------------------------------

    async def generate_report(
        self,
        format: str = "pdf",
        filters: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a report in the specified format.

        This is the main entry point called by the
        ``ReportGenerationWorker``. It validates the format, gathers
        data, delegates to the format-specific generator, and persists
        the output.

        Args:
            format: Output format — one of ``pdf``, ``excel``, ``csv``,
                ``json`` (default: ``"pdf"``).
            filters: Optional filter parameters (date ranges, video IDs,
                etc.).
            options: Optional rendering options (title, orientation,
                etc.).

        Returns:
            Dictionary with report metadata including file path,
            format, and size.

        Raises:
            ValidationError: If *format* is invalid.
            StorageError: If data gathering or persistence fails.
            ReportError: If report generation fails.
        """
        fmt = format.lower().strip()
        if fmt not in _VALID_FORMATS:
            raise ValidationError(
                f"Invalid report format '{format}'. "
                f"Valid formats: {', '.join(sorted(_VALID_FORMATS))}."
            )

        logger.info(
            "Generating report: format='%s', filters=%s, options=%s",
            fmt,
            filters or {},
            options or {},
        )

        # Gather report data
        try:
            report_data = self._gather_report_data(filters or {})
        except StorageError as exc:
            raise StorageError(
                f"Failed to gather data for report: {exc}"
            ) from exc

        # Generate report based on format
        if fmt == "pdf":
            result = self._generate_pdf_report(report_data, options or {})
        elif fmt == "excel":
            result = self._generate_excel_report(report_data, options or {})
        elif fmt == "csv":
            result = self._generate_csv_report(report_data, options or {})
        elif fmt == "json":
            result = self._generate_json_report(report_data, options or {})
        else:
            raise ValidationError(f"Unsupported format: '{fmt}'.")

        logger.info(
            "Report generated: format='%s', path='%s'",
            fmt,
            result.get("file_path", "N/A"),
        )
        return result

    # ------------------------------------------------------------------
    # Format-Specific Generators
    # ------------------------------------------------------------------

    async def generate_pdf(
        self,
        filters: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a PDF report.

        Args:
            filters: Optional filter parameters.
            options: Optional rendering options.

        Returns:
            Dictionary with report metadata.
        """
        return await self.generate_report(
            format="pdf", filters=filters, options=options
        )

    async def generate_excel(
        self,
        filters: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate an Excel report.

        Args:
            filters: Optional filter parameters.
            options: Optional rendering options.

        Returns:
            Dictionary with report metadata.
        """
        return await self.generate_report(
            format="excel", filters=filters, options=options
        )

    async def generate_json_report(
        self,
        filters: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate a JSON report.

        Args:
            filters: Optional filter parameters.
            options: Optional rendering options.

        Returns:
            Dictionary with report metadata.
        """
        return await self.generate_report(
            format="json", filters=filters, options=options
        )

    # ------------------------------------------------------------------
    # Internal: Report Data Gathering
    # ------------------------------------------------------------------

    def _gather_report_data(
        self,
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        """Gather data from CSV stores for report generation.

        Args:
            filters: Filter parameters (e.g. ``video_ids``, ``date_from``,
                ``date_to``).

        Returns:
            Dictionary with gathered data sections:
            - ``summary``: Overall summary counts.
            - ``detections``: Detection records.
            - ``events``: Business event records.
            - ``alerts``: Alert records.
            - ``kpis``: KPI records.
            - ``generated_at``: ISO-8601 timestamp.

        Raises:
            StorageError: If reading from stores fails.
        """
        video_ids: list[str] | None = None
        if "video_ids" in filters:
            vids = filters["video_ids"]
            if isinstance(vids, list) and vids:
                video_ids = [str(v) for v in vids]

        date_from = filters.get("date_from", "")
        date_to = filters.get("date_to", "")

        try:
            videos = self._storage.read_csv_store("videos")
            detections = self._storage.read_csv_store("detections")
            events = self._storage.read_csv_store("events")
            alerts = self._storage.read_csv_store("alerts")
            kpis = self._storage.read_csv_store("kpis")
        except StorageError as exc:
            raise StorageError(
                f"Failed to read data for report: {exc}"
            ) from exc

        # Apply filters
        if video_ids:
            videos = [v for v in videos if v.get("video_id") in video_ids]
            detections = [d for d in detections if d.get("video_id") in video_ids]
            events = [e for e in events if e.get("video_id") in video_ids]

        if date_from:
            detections = [
                d for d in detections
                if d.get("created_at", "") >= date_from
            ]
            events = [
                e for e in events
                if e.get("created_at", "") >= date_from
            ]

        if date_to:
            detections = [
                d for d in detections
                if d.get("created_at", "") <= date_to
            ]
            events = [
                e for e in events
                if e.get("created_at", "") <= date_to
            ]

        # Build summary
        class_counts: dict[str, int] = {}
        for d in detections:
            cls = d.get("class_name", "unknown")
            class_counts[cls] = class_counts.get(cls, 0) + 1

        severity_counts: dict[str, int] = {}
        for a in alerts:
            sev = a.get("severity", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "summary": {
                "total_videos": len(videos),
                "total_detections": len(detections),
                "total_events": len(events),
                "total_alerts": len(alerts),
                "total_kpis": len(kpis),
                "class_counts": class_counts,
                "severity_counts": severity_counts,
            },
            "videos": videos,
            "detections": detections,
            "events": events,
            "alerts": alerts,
            "kpis": kpis,
            "filters_applied": filters,
            "generated_at": now_utc().isoformat(),
        }

    # ------------------------------------------------------------------
    # Internal: PDF Report
    # ------------------------------------------------------------------

    def _generate_pdf_report(
        self,
        report_data: dict[str, Any],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a PDF report file.

        **Current implementation** creates a placeholder JSON file
        since PDF generation will be wired when the PDF library is
        integrated.

        Args:
            report_data: Gathered data for the report.
            options: Rendering options.

        Returns:
            Dictionary with report metadata.
        """
        report_id = generate_report_id()
        title = options.get("title", "VisionOps AI Report")
        filename = f"{report_id}_{title.replace(' ', '_')[:50]}.json"

        content = {
            "report_id": report_id,
            "format": "pdf",
            "title": title,
            "generated_at": now_utc().isoformat(),
            "summary": report_data.get("summary", {}),
        }

        # TODO: Wire actual PDF generation when available.
        #   from backend.reports.pdf import PDFGenerator
        #   generator = PDFGenerator()
        #   pdf_bytes = generator.generate(content, options)
        #   file_path = self._storage.file_manager.save_report_file(
        #       content=pdf_bytes,
        #       filename=filename.replace(".json", ".pdf"),
        #       report_type="pdf_reports",
        #   )

        # Placeholder: save as JSON
        file_path = self._save_report_json(content, filename, "pdf_reports")

        return {
            "report_id": report_id,
            "format": "pdf",
            "title": title,
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size if file_path else 0,
            "status": "generated",
            "generated_at": now_utc().isoformat(),
        }

    # ------------------------------------------------------------------
    # Internal: Excel Report
    # ------------------------------------------------------------------

    def _generate_excel_report(
        self,
        report_data: dict[str, Any],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate an Excel report file.

        **Current implementation** creates a placeholder JSON file
        since Excel generation will be wired when the Excel library is
        integrated.

        Args:
            report_data: Gathered data for the report.
            options: Rendering options.

        Returns:
            Dictionary with report metadata.
        """
        report_id = generate_report_id()
        title = options.get("title", "VisionOps AI Excel Report")
        filename = f"{report_id}_{title.replace(' ', '_')[:50]}.json"

        content = {
            "report_id": report_id,
            "format": "excel",
            "title": title,
            "generated_at": now_utc().isoformat(),
            "summary": report_data.get("summary", {}),
            "detections": report_data.get("detections", []),
            "events": report_data.get("events", []),
            "alerts": report_data.get("alerts", []),
        }

        # TODO: Wire actual Excel generation when available.
        #   from backend.reports.excel import ExcelGenerator
        #   generator = ExcelGenerator()
        #   excel_bytes = generator.generate(content, options)
        #   file_path = self._storage.file_manager.save_report_file(
        #       content=excel_bytes,
        #       filename=filename.replace(".json", ".xlsx"),
        #       report_type="excel_reports",
        #   )

        file_path = self._save_report_json(content, filename, "excel_reports")

        return {
            "report_id": report_id,
            "format": "excel",
            "title": title,
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size if file_path else 0,
            "status": "generated",
            "generated_at": now_utc().isoformat(),
        }

    # ------------------------------------------------------------------
    # Internal: CSV Report
    # ------------------------------------------------------------------

    def _generate_csv_report(
        self,
        report_data: dict[str, Any],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a CSV report file.

        **Current implementation** creates a placeholder JSON file
        since CSV generation will be wired when dedicated CSV export
        is needed.

        Args:
            report_data: Gathered data for the report.
            options: Rendering options.

        Returns:
            Dictionary with report metadata.
        """
        report_id = generate_report_id()
        title = options.get("title", "VisionOps AI CSV Report")
        filename = f"{report_id}_{title.replace(' ', '_')[:50]}.json"

        content = {
            "report_id": report_id,
            "format": "csv",
            "title": title,
            "generated_at": now_utc().isoformat(),
            "summary": report_data.get("summary", {}),
        }

        # TODO: Wire actual CSV generation when available.
        #   from backend.reports.csv import CSVGenerator
        #   generator = CSVGenerator()
        #   csv_bytes = generator.generate(report_data, options)
        #   file_path = self._storage.file_manager.save_report_file(
        #       content=csv_bytes,
        #       filename=filename.replace(".json", ".csv"),
        #       report_type="csv_reports",
        #   )

        file_path = self._save_report_json(content, filename, "json_reports")

        return {
            "report_id": report_id,
            "format": "csv",
            "title": title,
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size if file_path else 0,
            "status": "generated",
            "generated_at": now_utc().isoformat(),
        }

    # ------------------------------------------------------------------
    # Internal: JSON Report
    # ------------------------------------------------------------------

    def _generate_json_report(
        self,
        report_data: dict[str, Any],
        options: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a JSON report file.

        Serialises the report data to a JSON file in the configured
        JSON reports directory.

        Args:
            report_data: Gathered data for the report.
            options: Rendering options.

        Returns:
            Dictionary with report metadata.
        """
        report_id = generate_report_id()
        title = options.get("title", "VisionOps AI JSON Report")
        filename = f"{report_id}_{title.replace(' ', '_')[:50]}.json"

        content = {
            "report_id": report_id,
            "format": "json",
            "title": title,
            "generated_at": now_utc().isoformat(),
            "summary": report_data.get("summary", {}),
            "videos": report_data.get("videos", []),
            "detections": report_data.get("detections", []),
            "events": report_data.get("events", []),
            "alerts": report_data.get("alerts", []),
            "kpis": report_data.get("kpis", []),
            "filters_applied": report_data.get("filters_applied", {}),
        }

        file_path = self._save_report_json(content, filename, "json_reports")

        return {
            "report_id": report_id,
            "format": "json",
            "title": title,
            "file_path": str(file_path),
            "file_size": file_path.stat().st_size if file_path else 0,
            "status": "generated",
            "generated_at": now_utc().isoformat(),
        }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _save_report_json(
        self,
        content: dict[str, Any],
        filename: str,
        report_type: str,
    ) -> Path:
        """Serialize content to JSON and save via the storage layer.

        Args:
            content: Data to serialize.
            filename: Desired filename (with .json extension).
            report_type: Storage report type (e.g. ``pdf_reports``,
                ``excel_reports``, ``json_reports``).

        Returns:
            Resolved ``Path`` of the saved file.

        Raises:
            StorageError: If saving fails.
        """
        try:
            json_bytes = json.dumps(content, indent=2, default=str).encode(
                "utf-8"
            )
            path = self._storage.file_manager.save_report_file(
                content=json_bytes,
                filename=filename,
                report_type=report_type,
            )
            logger.info(
                "Report saved: %s (%d bytes)", path, len(json_bytes)
            )
            return path
        except (OSError, ValueError) as exc:
            raise StorageError(
                f"Failed to save report '{filename}': {exc}"
            ) from exc
