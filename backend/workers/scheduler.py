"""
VisionOps AI - Scheduler Module

Manages recurring background jobs using APScheduler's AsyncIOScheduler.
Supports startup/shutdown lifecycle, configurable intervals, cron
scheduling, retry on failure, job cancellation, and background execution.

All workers are registered with the scheduler and executed according to
their configured schedules. Configuration is loaded from
``core.config.settings``.

Usage:
    scheduler_manager = SchedulerManager()
    await scheduler_manager.startup()
    await scheduler_manager.register_worker(worker_instance, interval=300)
    await scheduler_manager.shutdown()
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.job import Job
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
    JobEvent,
)

from core.config import settings
from workers.base import BaseWorker


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_COALESCE: bool = True
DEFAULT_MAX_INSTANCES: int = 1
DEFAULT_MISFIRE_GRACE_TIME: int = 30
DEFAULT_SHUTDOWN_TIMEOUT: int = 30
MAX_HISTORY_SIZE: int = 100

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ExecutionRecord:
    """Record of a single scheduled job execution."""

    run_id: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    success: bool = False
    error: str | None = None


@dataclass
class ScheduledJob:
    """Represents a registered scheduled job."""

    name: str
    worker: BaseWorker
    job_id: str
    interval_seconds: int | None = None
    cron_expression: str | None = None
    apscheduler_job: Job | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_run_at: datetime | None = None
    last_result: Dict[str, Any] | None = None
    last_error: str | None = None
    is_running: bool = False
    execution_history: List[ExecutionRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the scheduled job info for monitoring."""
        return {
            "name": self.name,
            "job_id": self.job_id,
            "interval_seconds": self.interval_seconds,
            "cron_expression": self.cron_expression,
            "created_at": self.created_at.isoformat(),
            "last_run_at": (
                self.last_run_at.isoformat()
                if self.last_run_at is not None
                else None
            ),
            "is_running": self.is_running,
            "last_error": self.last_error,
            "worker_status": self.worker.status.value,
            "worker_version": self.worker.version,
            "recent_executions": len(self.execution_history),
        }


# ---------------------------------------------------------------------------
# Scheduler Manager
# ---------------------------------------------------------------------------


class SchedulerManager:
    """
    Manages the lifecycle and registration of all scheduled background jobs.

    Uses APScheduler's AsyncIOScheduler for reliable async scheduling
    with support for coalescing, misfire handling, execution events,
    and both interval and cron-based triggers.
    """

    def __init__(
        self,
        name: str | None = None,
        coalesce: bool | None = None,
        max_instances: int | None = None,
        misfire_grace_time: int | None = None,
    ) -> None:
        """
        Initialise the scheduler manager.

        All parameters fall back to values from ``core.config.settings``
        when not explicitly provided.

        Args:
            name: Display name for the scheduler instance.
            coalesce: If True, coalesce missed jobs into a single run.
            max_instances: Maximum number of concurrent job instances.
            misfire_grace_time: Seconds allowed for a job to be late.
        """
        self._name: str = name or getattr(
            settings, "SCHEDULER_NAME", "VisionOpsScheduler"
        )

        self._coalesce: bool = (
            coalesce
            if coalesce is not None
            else getattr(settings, "SCHEDULER_COALESCE", DEFAULT_COALESCE)
        )
        self._max_instances: int = (
            max_instances
            if max_instances is not None
            else getattr(settings, "SCHEDULER_MAX_INSTANCES", DEFAULT_MAX_INSTANCES)
        )
        self._misfire_grace_time: int = (
            misfire_grace_time
            if misfire_grace_time is not None
            else getattr(
                settings, "SCHEDULER_MISFIRE_GRACE_TIME", DEFAULT_MISFIRE_GRACE_TIME
            )
        )
        self._shutdown_timeout: int = getattr(
            settings, "SCHEDULER_SHUTDOWN_TIMEOUT", DEFAULT_SHUTDOWN_TIMEOUT
        )

        self._scheduler: AsyncIOScheduler = AsyncIOScheduler(
            coalesce=self._coalesce,
            max_instances=self._max_instances,
            misfire_grace_time=self._misfire_grace_time,
        )
        self._jobs: Dict[str, ScheduledJob] = {}
        self._is_running: bool = False
        self._shutdown_lock: asyncio.Lock = asyncio.Lock()

        self._logger: logging.Logger = logging.getLogger(
            f"visionops.workers.{self._name}"
        )
        self._logger.info(
            "Scheduler '%s' initialised | coalesce=%s | max_instances=%d | "
            "misfire_grace=%ds | shutdown_timeout=%ds",
            self._name,
            self._coalesce,
            self._max_instances,
            self._misfire_grace_time,
            self._shutdown_timeout,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Return the scheduler display name."""
        return self._name

    @property
    def is_running(self) -> bool:
        """Check whether the scheduler is currently running."""
        return self._is_running

    @property
    def scheduled_jobs(self) -> List[ScheduledJob]:
        """Return a list of all registered scheduled jobs."""
        return list(self._jobs.values())

    # ------------------------------------------------------------------
    # Lifecycle Methods
    # ------------------------------------------------------------------

    async def startup(self) -> None:
        """Start the APScheduler and begin processing recurring jobs."""
        if self._is_running:
            self._logger.warning(
                "Scheduler '%s' is already running.", self._name
            )
            return

        self._scheduler.add_listener(
            self._on_job_event,
            mask=EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED,
        )

        self._scheduler.start()
        self._is_running = True

        self._logger.info(
            "Scheduler '%s' started successfully.", self._name
        )

    async def shutdown(self, wait: bool = True) -> None:
        """
        Gracefully shut down the scheduler and all registered jobs.

        Args:
            wait: If True, wait for all running jobs to complete
                  (up to ``_shutdown_timeout`` seconds).
        """
        if not self._is_running:
            self._logger.warning(
                "Scheduler '%s' is not running.", self._name
            )
            return

        async with self._shutdown_lock:
            self._logger.info(
                "Scheduler '%s' shutting down ...", self._name
            )

            # Shutdown all workers gracefully
            for job_name, scheduled_job in self._jobs.items():
                self._logger.info(
                    "Shutting down worker '%s' ...", job_name
                )
                await scheduled_job.worker.shutdown()

            if wait:
                self._scheduler.shutdown(wait=True)
            else:
                self._scheduler.shutdown(wait=False)

            self._is_running = False

            self._logger.info(
                "Scheduler '%s' shut down successfully.", self._name
            )

    # ------------------------------------------------------------------
    # Job Registration
    # ------------------------------------------------------------------

    async def register_worker(
        self,
        worker: BaseWorker,
        interval_seconds: int | None = None,
        cron_expression: str | None = None,
        job_id: str | None = None,
    ) -> str:
        """
        Register a worker as a recurring scheduled job.

        Exactly one of ``interval_seconds`` or ``cron_expression`` must
        be provided.

        Args:
            worker: An instance of a BaseWorker subclass.
            interval_seconds: Interval between job runs in seconds.
            cron_expression: Cron expression for scheduling
                (e.g., '0 */2 * * *' for every 2 hours).
            job_id: Optional custom job identifier (auto-generated if None).

        Returns:
            The job identifier string.

        Raises:
            TypeError: If ``worker`` is not a BaseWorker instance.
            ValueError: If neither or both scheduling options are provided.
        """
        if not isinstance(worker, BaseWorker):
            raise TypeError(
                f"Expected BaseWorker instance, got {type(worker).__name__}."
            )

        if interval_seconds is None and cron_expression is None:
            raise ValueError(
                "Either 'interval_seconds' or 'cron_expression' must be provided."
            )
        if interval_seconds is not None and cron_expression is not None:
            raise ValueError(
                "Only one of 'interval_seconds' or 'cron_expression' "
                "should be provided, not both."
            )

        # Validate worker before registration
        await self._validate_worker(worker)

        actual_job_id: str = job_id or f"{worker.name}_{id(worker)}"

        if actual_job_id in self._jobs:
            self._logger.warning(
                "Job '%s' is already registered. Skipping duplicate.",
                actual_job_id,
            )
            return actual_job_id

        # Build the appropriate trigger
        if interval_seconds is not None:
            trigger = IntervalTrigger(seconds=max(interval_seconds, 10))
            resolved_interval = max(interval_seconds, 10)
        else:
            trigger = CronTrigger.from_crontab(cron_expression)
            resolved_interval = 0  # not applicable for cron

        apscheduler_job: Job = self._scheduler.add_job(
            func=self._run_worker_job,
            trigger=trigger,
            args=[worker, actual_job_id],
            id=actual_job_id,
            name=worker.name,
            replace_existing=True,
            coalesce=self._coalesce,
            max_instances=self._max_instances,
            misfire_grace_time=self._misfire_grace_time,
        )

        scheduled_job: ScheduledJob = ScheduledJob(
            name=worker.name,
            worker=worker,
            job_id=actual_job_id,
            interval_seconds=resolved_interval if interval_seconds else None,
            cron_expression=cron_expression,
            apscheduler_job=apscheduler_job,
        )

        self._jobs[actual_job_id] = scheduled_job

        schedule_desc: str = (
            f"interval={resolved_interval}s"
            if interval_seconds
            else f"cron='{cron_expression}'"
        )
        self._logger.info(
            "Registered worker '%s' as job '%s' (%s).",
            worker.name,
            actual_job_id,
            schedule_desc,
        )

        return actual_job_id

    async def unregister_worker(self, job_id: str) -> bool:
        """
        Remove a scheduled job from the scheduler.

        Args:
            job_id: The identifier of the job to remove.

        Returns:
            True if the job was found and removed, False otherwise.
        """
        if job_id not in self._jobs:
            self._logger.warning(
                "Job '%s' not found. Cannot unregister.", job_id
            )
            return False

        scheduled_job: ScheduledJob = self._jobs.pop(job_id)

        if scheduled_job.apscheduler_job is not None:
            scheduled_job.apscheduler_job.remove()

        await scheduled_job.worker.shutdown()

        self._logger.info(
            "Unregistered worker '%s' (job '%s').",
            scheduled_job.name,
            job_id,
        )

        return True

    # ------------------------------------------------------------------
    # Worker Validation
    # ------------------------------------------------------------------

    @staticmethod
    async def _validate_worker(worker: BaseWorker) -> None:
        """
        Validate that a worker is correctly configured before registration.

        Args:
            worker: The worker instance to validate.

        Raises:
            ValueError: If validation fails.
        """
        if not worker.name:
            raise ValueError("Worker must have a non-empty name.")

        if not hasattr(worker, "execute_async") or not callable(
            worker.execute_async
        ):
            raise ValueError(
                f"Worker '{worker.name}' must implement 'execute_async'."
            )

    # ------------------------------------------------------------------
    # Job Execution
    # ------------------------------------------------------------------

    async def _run_worker_job(
        self,
        worker: BaseWorker,
        job_id: str,
    ) -> None:
        """Execute a worker job and track its result."""
        scheduled_job: ScheduledJob | None = self._jobs.get(job_id)

        if scheduled_job is not None:
            scheduled_job.is_running = True
            scheduled_job.last_run_at = datetime.now(timezone.utc)

        exec_record = ExecutionRecord(
            run_id=id(worker),
            started_at=datetime.now(timezone.utc),
        )

        try:
            result: Dict[str, Any] = await worker.run(
                job_id=job_id,
                payload={"scheduled": True},
            )

            if scheduled_job is not None:
                scheduled_job.last_result = result
                scheduled_job.last_error = None

            exec_record.success = True
            exec_record.completed_at = datetime.now(timezone.utc)
            exec_record.duration_seconds = (
                exec_record.completed_at - exec_record.started_at
            ).total_seconds()

        except Exception as exc:
            self._logger.error(
                "Scheduled job '%s' failed: %s", job_id, exc
            )

            if scheduled_job is not None:
                scheduled_job.last_error = str(exc)

            exec_record.success = False
            exec_record.error = str(exc)
            exec_record.completed_at = datetime.now(timezone.utc)
            exec_record.duration_seconds = (
                exec_record.completed_at - exec_record.started_at
            ).total_seconds()

        finally:
            if scheduled_job is not None:
                scheduled_job.is_running = False
                # Append execution history, trim to max size
                scheduled_job.execution_history.append(exec_record)
                if len(scheduled_job.execution_history) > MAX_HISTORY_SIZE:
                    scheduled_job.execution_history = (
                        scheduled_job.execution_history[-MAX_HISTORY_SIZE:]
                    )

    # ------------------------------------------------------------------
    # Event Listeners
    # ------------------------------------------------------------------

    def _on_job_event(self, event: JobEvent) -> None:
        """Handle APScheduler job execution events."""
        job_id: str = event.job_id

        if event.code == EVENT_JOB_EXECUTED:
            self._logger.debug(
                "Job '%s' executed successfully.", job_id
            )
        elif event.code == EVENT_JOB_ERROR:
            self._logger.error(
                "Job '%s' raised an exception.", job_id
            )
        elif event.code == EVENT_JOB_MISSED:
            self._logger.warning(
                "Job '%s' was missed (misfired).", job_id
            )

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_job(self, job_id: str) -> ScheduledJob | None:
        """Return the scheduled job metadata by identifier."""
        return self._jobs.get(job_id)

    def get_worker_status(self, job_id: str) -> Dict[str, Any] | None:
        """Return the status report for a specific worker by job ID."""
        scheduled_job: ScheduledJob | None = self._jobs.get(job_id)
        if scheduled_job is None:
            return None
        return scheduled_job.worker.get_status_report()

    def get_all_status_reports(self) -> List[Dict[str, Any]]:
        """Return status reports for all registered workers."""
        return [
            scheduled_job.worker.get_status_report()
            for scheduled_job in self._jobs.values()
        ]

    def get_job_execution_history(
        self, job_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Return the execution history for a specific job.

        Args:
            job_id: The job identifier.
            limit: Maximum number of recent records to return.

        Returns:
            List of execution record dictionaries.
        """
        scheduled_job: ScheduledJob | None = self._jobs.get(job_id)
        if scheduled_job is None:
            return []

        recent = scheduled_job.execution_history[-limit:]
        return [
            {
                "run_id": str(rec.run_id),
                "started_at": rec.started_at.isoformat(),
                "completed_at": (
                    rec.completed_at.isoformat()
                    if rec.completed_at
                    else None
                ),
                "duration_seconds": rec.duration_seconds,
                "success": rec.success,
                "error": rec.error,
            }
            for rec in recent
        ]

    # ------------------------------------------------------------------
    # Health / Summary
    # ------------------------------------------------------------------

    def health(self) -> Dict[str, Any]:
        """Return a health check report for the scheduler."""
        total_jobs: int = len(self._jobs)
        running_jobs: int = sum(
            1 for j in self._jobs.values() if j.is_running
        )
        failed_jobs: int = sum(
            1
            for j in self._jobs.values()
            if j.last_error is not None
        )

        return {
            "scheduler": self._name,
            "is_running": self._is_running,
            "total_jobs": total_jobs,
            "running_jobs": running_jobs,
            "failed_jobs": failed_jobs,
            "healthy": self._is_running and failed_jobs == 0,
        }

    def summary(self) -> Dict[str, Any]:
        """Return a summary of the scheduler and all registered jobs."""
        return {
            "scheduler": self._name,
            "is_running": self._is_running,
            "total_jobs": len(self._jobs),
            "jobs": [
                scheduled_job.to_dict()
                for scheduled_job in self._jobs.values()
            ],
        }
