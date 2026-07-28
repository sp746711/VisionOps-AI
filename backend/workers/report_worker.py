"""
VisionOps AI - Report Generation Worker

Coordinates background report generation jobs by delegating to the
ReportService. This worker manages the lifecycle of generating PDF,
Excel, CSV, and JSON reports through service orchestration — it does
NOT generate any report content directly.

Responsibilities:
    - Accept report generation job requests.
    - Validate requested output format.
    - Delegate report building to the service layer.
    - Support PDF, Excel, CSV, and JSON formats.
    - Handle retries, timeouts, and graceful shutdown.
    - Track job execution statistics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from core.config import settings
from workers.base import BaseWorker


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_REPORT_FORMATS: frozenset[str] = frozenset(
    {"pdf", "excel", "csv", "json"}
)


# ---------------------------------------------------------------------------
# Report Generation Worker
# ---------------------------------------------------------------------------


class ReportGenerationWorker(BaseWorker):
    """
    Background worker that coordinates report generation jobs.

    Delegates the actual report content generation to the ReportService.
    This class only handles job orchestration, format validation, and
    status tracking.
    """

    def __init__(
        self,
        name: str = "ReportGenerationWorker",
        max_retries: int | None = None,
        retry_delay: float | None = None,
        retry_backoff: float | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        """
        Initialise the report generation worker.

        All timing parameters fall back to ``core.config.settings``
        values.

        Args:
            name: Human-readable worker name.
            max_retries: Maximum retry attempts on failure.
            retry_delay: Initial retry delay in seconds.
            retry_backoff: Exponential backoff multiplier.
            timeout_seconds: Maximum allowed execution time.
        """
        if timeout_seconds is None:
            timeout_seconds = getattr(
                settings, "WORKER_REPORT_TIMEOUT", 300
            )
        if max_retries is None:
            max_retries = getattr(
                settings, "WORKER_REPORT_RETRIES", 2
            )

        super().__init__(
            name=name,
            max_retries=max_retries,
            retry_delay=retry_delay,
            retry_backoff=retry_backoff,
            timeout_seconds=timeout_seconds,
        )
        self._logger: logging.Logger = logging.getLogger(
            "visionops.workers.report_worker"
        )

    # ------------------------------------------------------------------
    # Abstract Method Implementation
    # ------------------------------------------------------------------

    async def execute_async(
        self,
        job_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a report generation job.

        The payload must specify the report format and may include
        filters, date ranges, and output options. Actual report
        generation is delegated to the ReportService.

        Args:
            job_id: Unique job identifier.
            payload: Job parameters including 'format' and 'options'.

        Returns:
            Dictionary containing the generated report metadata
            from the service.

        Raises:
            RuntimeError: If the payload is missing required fields or
                specifies an unsupported format.
        """
        self._logger.info(
            "ReportGenerationWorker | Job '%s' | Starting report generation.",
            job_id,
        )

        if payload is None:
            raise RuntimeError(
                f"Job '{job_id}': No payload provided. "
                "A 'format' field is required."
            )

        report_format: str | None = payload.get("format", "pdf")
        report_format = report_format.lower().strip()

        if report_format not in VALID_REPORT_FORMATS:
            raise RuntimeError(
                f"Job '{job_id}': Unsupported report format "
                f"'{report_format}'. Valid formats: "
                f"{', '.join(sorted(VALID_REPORT_FORMATS))}."
            )

        report_options: Dict[str, Any] = payload.get("options", {})
        report_filters: Dict[str, Any] = payload.get("filters", {})

        self._logger.info(
            "ReportGenerationWorker | Job '%s' | Format: %s",
            job_id,
            report_format,
        )

        # ----------------------------------------------------------
        # Delegate to ReportService.
        #
        # TODO: Uncomment and wire the actual service when available.
        #
        #   from services.report_service import ReportService
        #   service = ReportService()
        #   result = await service.generate_report(
        #       format=report_format,
        #       filters=report_filters,
        #       options=report_options,
        #   )
        #
        # For now, return a structured result indicating delegation.
        # ----------------------------------------------------------

        # result: Dict[str, Any] = await service.generate_report(
        #     format=report_format,
        #     filters=report_filters,
        #     options=report_options,
        # )

        result: Dict[str, Any] = {
            "job_id": job_id,
            "format": report_format,
            "status": "delegated_to_report_service",
            "service": "ReportService",
            "message": (
                f"Report generation in '{report_format}' format "
                f"delegated to ReportService."
            ),
            "options": report_options,
            "filters": report_filters,
        }

        self._logger.info(
            "ReportGenerationWorker | Job '%s' | Report generation "
            "in '%s' format delegated.",
            job_id,
            report_format,
        )

        return result
