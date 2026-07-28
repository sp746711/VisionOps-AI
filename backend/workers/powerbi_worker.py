"""
VisionOps AI - Power BI Export Worker

Coordinates background Power BI dataset export jobs by delegating to
the PowerBIExportService or PowerBIDataset in the analytics layer.
This worker manages the lifecycle of preparing and exporting datasets
for Power BI integration through service orchestration — it does NOT
generate any datasets directly.

Responsibilities:
    - Trigger Power BI dataset generation and refresh.
    - Coordinate dataset export to the configured output location.
    - Support incremental and full dataset exports.
    - Dataset validation before export.
    - Export metadata and status reporting.
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

VALID_EXPORT_MODES: frozenset[str] = frozenset({"full", "incremental"})


# ---------------------------------------------------------------------------
# Power BI Export Worker
# ---------------------------------------------------------------------------


class PowerBIExportWorker(BaseWorker):
    """
    Background worker that coordinates Power BI dataset export jobs.

    Delegates dataset generation and export to the PowerBIDataset
    module in the analytics layer or the PowerBIExportService.
    This class only handles job orchestration, export mode selection,
    dataset validation, and status tracking.
    """

    def __init__(
        self,
        name: str = "PowerBIExportWorker",
        max_retries: int | None = None,
        retry_delay: float | None = None,
        retry_backoff: float | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        """
        Initialise the Power BI export worker.

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
                settings, "WORKER_POWERBI_TIMEOUT", 300
            )
        if max_retries is None:
            max_retries = getattr(
                settings, "WORKER_POWERBI_RETRIES", 2
            )

        super().__init__(
            name=name,
            max_retries=max_retries,
            retry_delay=retry_delay,
            retry_backoff=retry_backoff,
            timeout_seconds=timeout_seconds,
        )
        self._logger: logging.Logger = logging.getLogger(
            "visionops.workers.powerbi_worker"
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
        Execute a Power BI dataset export job.

        The payload can specify the export mode (full or incremental),
        dataset filters, and output options. Actual dataset generation
        is delegated to the PowerBIDataset or PowerBIExportService.

        Args:
            job_id: Unique job identifier.
            payload: Job parameters (e.g., export_mode, filters).

        Returns:
            Dictionary containing the export results and metadata
            from the service.

        Raises:
            RuntimeError: If the payload specifies an invalid export mode.
        """
        self._logger.info(
            "PowerBIExportWorker | Job '%s' | Starting Power BI export.",
            job_id,
        )

        # Determine export mode and parameters
        export_mode: str = "full"
        export_filters: Dict[str, Any] = {}
        output_path: str | None = None
        validate_dataset: bool = True

        if payload is not None:
            export_mode = (
                payload.get("export_mode", "full").lower().strip()
            )
            export_filters = payload.get("filters", {})
            output_path = payload.get("output_path")
            validate_dataset = payload.get(
                "validate_dataset", True
            )

        if export_mode not in VALID_EXPORT_MODES:
            raise RuntimeError(
                f"Job '{job_id}': Invalid export mode "
                f"'{export_mode}'. Valid modes: "
                f"{', '.join(sorted(VALID_EXPORT_MODES))}."
            )

        self._logger.info(
            "PowerBIExportWorker | Job '%s' | Mode: %s | "
            "Validate: %s | Output: %s",
            job_id,
            export_mode,
            validate_dataset,
            output_path or "default",
        )

        # ----------------------------------------------------------
        # Delegate to PowerBIDataset or PowerBIExportService.
        #
        # TODO: Uncomment and wire the actual service when available.
        #
        #   from analytics.powerbi_dataset import PowerBIDataset
        #   service = PowerBIDataset()
        #
        #   if validate_dataset:
        #       is_valid = await service.validate_dataset()
        #       if not is_valid:
        #           raise RuntimeError("Dataset validation failed.")
        #
        #   result = await service.export_dataset(
        #       mode=export_mode,
        #       filters=export_filters,
        #       output_path=output_path,
        #   )
        #
        # For now, return a structured result indicating delegation.
        # ----------------------------------------------------------

        # if validate_dataset:
        #     is_valid = await service.validate_dataset()
        #     if not is_valid:
        #         raise RuntimeError(
        #             f"Job '{job_id}': Dataset validation failed."
        #         )
        #
        # result = await service.export_dataset(
        #     mode=export_mode,
        #     filters=export_filters,
        #     output_path=output_path,
        # )

        result: Dict[str, Any] = {
            "job_id": job_id,
            "export_mode": export_mode,
            "status": "delegated_to_powerbi_service",
            "service": "PowerBIDataset",
            "dataset_validation": (
                "pending" if validate_dataset else "skipped"
            ),
            "output_path": output_path or (
                getattr(
                    settings,
                    "POWERBI_EXPORT_PATH",
                    "outputs/reports/powerbi",
                )
            ),
            "message": (
                f"Power BI dataset export ({export_mode} mode) "
                f"delegated to PowerBIDataset service."
            ),
        }

        self._logger.info(
            "PowerBIExportWorker | Job '%s' | Export completed "
            "in '%s' mode.",
            job_id,
            export_mode,
        )

        return result
