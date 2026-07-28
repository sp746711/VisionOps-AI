"""
VisionOps AI - Cleanup Worker

Coordinates background cleanup and maintenance jobs for the system.
This worker manages data archiving, old file purging, temporary file
cleanup, and storage optimisation by delegating to the ArchiveManager
or CleanupService.

Responsibilities:
    - Archive old processed data and outputs.
    - Purge expired temporary files.
    - Clean up stale detection images and frames.
    - Optimise storage usage.
    - Configurable retention policy from settings.
    - Handle retries, timeouts, and graceful shutdown.
    - Track job execution statistics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from core.config import settings
from workers.base import BaseWorker


# ---------------------------------------------------------------------------
# Cleanup Worker
# ---------------------------------------------------------------------------


class CleanupWorker(BaseWorker):
    """
    Background worker that coordinates system cleanup and maintenance jobs.

    Delegates archive and purge operations to the ArchiveManager or
    CleanupService. This class only handles job orchestration,
    retention policy enforcement (from config), and status tracking.
    """

    def __init__(
        self,
        name: str = "CleanupWorker",
        max_retries: int | None = None,
        retry_delay: float | None = None,
        retry_backoff: float | None = None,
        timeout_seconds: float | None = None,
        retention_days: int | None = None,
    ) -> None:
        """
        Initialise the cleanup worker.

        All timing and retention parameters fall back to
        ``core.config.settings`` values.

        Args:
            name: Human-readable worker name.
            max_retries: Maximum retry attempts on failure.
            retry_delay: Initial retry delay in seconds.
            retry_backoff: Exponential backoff multiplier.
            timeout_seconds: Maximum allowed execution time.
            retention_days: Number of days to retain data before cleanup.
        """
        if timeout_seconds is None:
            timeout_seconds = getattr(
                settings, "WORKER_CLEANUP_TIMEOUT", 600
            )
        if max_retries is None:
            max_retries = getattr(
                settings, "WORKER_CLEANUP_RETRIES", 1
            )
        if retention_days is None:
            retention_days = getattr(
                settings, "WORKER_CLEANUP_RETENTION_DAYS", 30
            )

        super().__init__(
            name=name,
            max_retries=max_retries,
            retry_delay=retry_delay,
            retry_backoff=retry_backoff,
            timeout_seconds=timeout_seconds,
        )
        self._retention_days: int = max(retention_days, 1)
        self._logger: logging.Logger = logging.getLogger(
            "visionops.workers.cleanup_worker"
        )
        self._logger.info(
            "CleanupWorker initialised | timeout=%ds | max_retries=%d | "
            "retention=%d days",
            self._timeout_seconds,
            self._max_retries,
            self._retention_days,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def retention_days(self) -> int:
        """Return the current retention period in days (from config)."""
        return self._retention_days

    # ------------------------------------------------------------------
    # Abstract Method Implementation
    # ------------------------------------------------------------------

    async def execute_async(
        self,
        job_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a system cleanup job.

        The payload can specify which areas to clean (e.g., archives,
        temp files, old outputs). Actual cleanup operations are
        delegated to the ArchiveManager or CleanupService.

        Args:
            job_id: Unique job identifier.
            payload: Job parameters (e.g., target areas, retention override).

        Returns:
            Dictionary containing cleanup results and statistics
            from the service.
        """
        self._logger.info(
            "CleanupWorker | Job '%s' | Starting cleanup.",
            job_id,
        )

        # Determine retention and targets
        retention: int = self._retention_days
        targets: list[str] = ["archives", "temp", "outputs", "logs"]

        if payload is not None:
            retention = payload.get("retention_days", self._retention_days)
            targets = payload.get("targets", targets)

        self._logger.info(
            "CleanupWorker | Job '%s' | Retention: %d days | Targets: %s",
            job_id,
            retention,
            targets,
        )

        # ----------------------------------------------------------
        # Delegate to ArchiveManager or CleanupService.
        #
        # TODO: Uncomment and wire the actual service when available.
        #
        #   from storage.archive_manager import ArchiveManager
        #   service = ArchiveManager()
        #   result = await service.cleanup(
        #       retention_days=retention,
        #       targets=targets,
        #   )
        #
        # For now, return a structured result indicating delegation.
        # ----------------------------------------------------------

        # result: Dict[str, Any] = await service.cleanup(
        #     retention_days=retention,
        #     targets=targets,
        # )

        result: Dict[str, Any] = {
            "job_id": job_id,
            "status": "delegated_to_archive_manager",
            "service": "ArchiveManager",
            "retention_days": retention,
            "targets": targets,
            "message": (
                f"Cleanup for targets {targets} delegated to "
                f"ArchiveManager with {retention}-day retention."
            ),
        }

        self._logger.info(
            "CleanupWorker | Job '%s' | Cleanup delegated to ArchiveManager.",
            job_id,
        )

        return result
