"""
VisionOps AI - Base Worker Module

Provides the abstract base class for all background workers in the system.
Implements common patterns such as retry logic, timeout handling, graceful
shutdown via asyncio events, execution statistics, structured logging,
concurrency safety via asyncio.Lock, lifecycle hooks, and configuration
injection.

Every concrete worker MUST inherit from BaseWorker and implement the
abstract ``execute_async`` method.

Usage:
    class MyWorker(BaseWorker):
        async def execute_async(self, job_id: str, payload: dict | None = None) -> dict:
            # worker implementation — delegate to services only
            ...
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from core.config import settings


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_MAX_RETRIES: int = settings.WORKER_MAX_RETRIES if hasattr(settings, "WORKER_MAX_RETRIES") else 3
DEFAULT_RETRY_DELAY: float = 1.0
DEFAULT_RETRY_BACKOFF: float = 2.0
DEFAULT_TIMEOUT_SECONDS: float = settings.WORKER_TIMEOUT_SECONDS if hasattr(settings, "WORKER_TIMEOUT_SECONDS") else 300.0

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WorkerStatus(str, Enum):
    """Possible states for a worker's execution lifecycle."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ExecutionStats:
    """Tracks execution statistics for a worker instance."""

    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    timed_out_runs: int = 0
    cancelled_runs: int = 0
    total_execution_time: float = 0.0
    min_execution_time: float = float("inf")
    max_execution_time: float = 0.0
    last_execution_time: float | None = None
    last_error: str | None = None
    last_run_at: float | None = None
    last_run_id: str | None = None

    @property
    def avg_execution_time(self) -> float:
        """Calculate the average execution time across all runs."""
        if self.total_runs == 0:
            return 0.0
        return self.total_execution_time / self.total_runs

    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_runs == 0:
            return 100.0
        return (self.successful_runs / self.total_runs) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize stats to a dictionary for reporting."""
        return {
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "timed_out_runs": self.timed_out_runs,
            "cancelled_runs": self.cancelled_runs,
            "total_execution_time_seconds": round(self.total_execution_time, 4),
            "avg_execution_time_seconds": round(self.avg_execution_time, 4),
            "min_execution_time_seconds": (
                round(self.min_execution_time, 4)
                if self.min_execution_time != float("inf")
                else 0.0
            ),
            "max_execution_time_seconds": round(self.max_execution_time, 4),
            "last_execution_time_seconds": (
                round(self.last_execution_time, 4)
                if self.last_execution_time is not None
                else None
            ),
            "success_rate_percent": round(self.success_rate, 2),
            "last_error": self.last_error,
            "last_run_at": self.last_run_at,
            "last_run_id": self.last_run_id,
        }


# ---------------------------------------------------------------------------
# Base Worker (Abstract)
# ---------------------------------------------------------------------------


class BaseWorker(ABC):
    """
    Abstract base class for all VisionOps AI background workers.

    Provides:
        - Structured logging with a worker-specific logger.
        - Retry mechanism with configurable attempts and exponential backoff.
        - Timeout handling via ``asyncio.wait_for``.
        - Graceful shutdown via an internal ``asyncio.Event``.
        - Execution statistics tracking (``ExecutionStats``).
        - Job status reporting (``WorkerStatus``).
        - Concurrency safety via ``asyncio.Lock``.
        - Lifecycle hooks: ``_on_start``, ``_on_complete``, ``_on_failure``.
        - Configuration injection from ``core.config.settings``.
        - Execution metadata (run_id, timestamps, config snapshot).

    Subclasses must implement ``execute_async``.
    """

    def __init__(
        self,
        name: str | None = None,
        max_retries: int | None = None,
        retry_delay: float | None = None,
        retry_backoff: float | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        """
        Initialise the base worker.

        All numeric parameters fall back to values from
        ``core.config.settings`` when not explicitly provided.

        Args:
            name: Human-readable worker name (defaults to class name).
            max_retries: Maximum number of retry attempts on failure.
            retry_delay: Initial delay in seconds before the first retry.
            retry_backoff: Multiplier for the retry delay after each attempt.
            timeout_seconds: Maximum allowed execution time in seconds.
        """
        self._name: str = name or self.__class__.__name__

        # Load configuration from settings with overrides
        self._max_retries: int = (
            max_retries
            if max_retries is not None
            else getattr(settings, "WORKER_MAX_RETRIES", DEFAULT_MAX_RETRIES)
        )
        self._max_retries = max(self._max_retries, 0)

        self._retry_delay: float = (
            retry_delay
            if retry_delay is not None
            else getattr(settings, "WORKER_RETRY_DELAY", DEFAULT_RETRY_DELAY)
        )
        self._retry_delay = max(self._retry_delay, 0.1)

        self._retry_backoff: float = (
            retry_backoff
            if retry_backoff is not None
            else getattr(settings, "WORKER_RETRY_BACKOFF", DEFAULT_RETRY_BACKOFF)
        )
        self._retry_backoff = max(self._retry_backoff, 1.0)

        self._timeout_seconds: float = (
            timeout_seconds
            if timeout_seconds is not None
            else getattr(settings, "WORKER_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
        )
        self._timeout_seconds = max(self._timeout_seconds, 1.0)

        # Store a snapshot of relevant configuration for metadata
        self._config_snapshot: Dict[str, Any] = {
            "max_retries": self._max_retries,
            "retry_delay": self._retry_delay,
            "retry_backoff": self._retry_backoff,
            "timeout_seconds": self._timeout_seconds,
        }

        # Version for tracking worker implementation
        self._version: str = "2.0.0"

        # Concurrency safety
        self._lock: asyncio.Lock = asyncio.Lock()

        # Shutdown coordination
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._current_task: asyncio.Task | None = None

        # Execution tracking
        self._status: WorkerStatus = WorkerStatus.IDLE
        self._stats: ExecutionStats = ExecutionStats()

        # Logger
        self._logger: logging.Logger = logging.getLogger(
            f"visionops.workers.{self._name}"
        )
        self._logger.info(
            "Worker '%s' v%s initialised | max_retries=%d | timeout=%ds | "
            "retry_delay=%.1f | backoff=%.1f",
            self._name,
            self._version,
            self._max_retries,
            self._timeout_seconds,
            self._retry_delay,
            self._retry_backoff,
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Return the worker's display name."""
        return self._name

    @property
    def version(self) -> str:
        """Return the worker implementation version."""
        return self._version

    @property
    def status(self) -> WorkerStatus:
        """Return the current worker status."""
        return self._status

    @property
    def stats(self) -> ExecutionStats:
        """Return a reference to the execution statistics."""
        return self._stats

    @property
    def is_shutdown_requested(self) -> bool:
        """Check whether a graceful shutdown has been requested."""
        return self._shutdown_event.is_set()

    # ------------------------------------------------------------------
    # Abstract Method
    # ------------------------------------------------------------------

    @abstractmethod
    async def execute_async(
        self,
        job_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute the worker's core background job.

        Subclasses MUST override this method. It should only orchestrate
        calls to existing service layers; it must NOT contain business
        logic, AI algorithms, or API endpoint code.

        Args:
            job_id: Unique identifier for the job being executed.
            payload: Optional dictionary of input parameters.

        Returns:
            A dictionary containing the results of the execution.

        Raises:
            Exception: Any exception raised during execution will be
                handled by the retry mechanism in ``run``.
        """
        ...

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(
        self,
        job_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute the worker with retry, timeout, and shutdown support.

        This is the main entry point called by the scheduler or
        directly by the system. It wraps ``execute_async`` with
        retry logic, timeout enforcement, shutdown awareness, and
        lifecycle hooks.

        Args:
            job_id: Unique job identifier.
            payload: Optional input payload.

        Returns:
            Result dictionary from the successful execution.
        """
        if self.is_shutdown_requested:
            self._logger.warning(
                "Worker '%s' refused job '%s': shutdown in progress.",
                self._name,
                job_id,
            )
            return {
                "job_id": job_id,
                "status": WorkerStatus.CANCELLED.value,
                "error": "Worker is shutting down.",
            }

        async with self._lock:
            run_id: str = uuid.uuid4().hex[:12]
            self._status = WorkerStatus.RUNNING
            self._stats.total_runs += 1
            self._stats.last_run_id = run_id

            self._logger.info(
                "Worker '%s' | Job '%s' | Run '%s' | Starting.",
                self._name,
                job_id,
                run_id,
            )

            # Lifecycle hook: on_start
            await self._on_start(job_id, payload, run_id)

            last_exception: Exception | None = None
            attempt: int = 0
            delay: float = self._retry_delay

            while attempt <= self._max_retries:
                attempt += 1
                self._logger.info(
                    "Worker '%s' | Job '%s' | Attempt %d/%d",
                    self._name,
                    job_id,
                    attempt,
                    self._max_retries + 1,
                )

                try:
                    result: dict[str, Any] = await self._execute_with_timeout(
                        job_id, payload, run_id,
                    )

                    # Execution succeeded
                    self._status = WorkerStatus.COMPLETED
                    self._stats.successful_runs += 1

                    # Attach execution metadata to result
                    result["_metadata"] = {
                        "worker": self._name,
                        "version": self._version,
                        "run_id": run_id,
                        "status": WorkerStatus.COMPLETED.value,
                        "attempt": attempt,
                        "config": self._config_snapshot,
                    }

                    # Lifecycle hook: on_complete
                    await self._on_complete(job_id, result, run_id)

                    self._logger.info(
                        "Worker '%s' | Job '%s' | Run '%s' | "
                        "Completed successfully on attempt %d.",
                        self._name,
                        job_id,
                        run_id,
                        attempt,
                    )
                    return result

                except asyncio.TimeoutError:
                    self._stats.timed_out_runs += 1
                    self._status = WorkerStatus.TIMEOUT
                    error_msg = (
                        f"Job '{job_id}' timed out after "
                        f"{self._timeout_seconds}s."
                    )
                    self._logger.error(
                        "Worker '%s' | Run '%s' | %s",
                        self._name,
                        run_id,
                        error_msg,
                    )
                    last_exception = asyncio.TimeoutError(error_msg)
                    break

                except asyncio.CancelledError:
                    self._stats.cancelled_runs += 1
                    self._status = WorkerStatus.CANCELLED
                    self._logger.warning(
                        "Worker '%s' | Run '%s' | Job '%s' was cancelled.",
                        self._name,
                        run_id,
                        job_id,
                    )
                    raise

                except Exception as exc:
                    last_exception = exc
                    self._logger.error(
                        "Worker '%s' | Run '%s' | Job '%s' | "
                        "Attempt %d failed: %s",
                        self._name,
                        run_id,
                        job_id,
                        attempt,
                        exc,
                    )

                    if attempt > self._max_retries:
                        self._logger.warning(
                            "Worker '%s' | Run '%s' | Job '%s' | "
                            "No more retries.",
                            self._name,
                            run_id,
                            job_id,
                        )
                        break

                    self._logger.info(
                        "Worker '%s' | Run '%s' | Job '%s' | "
                        "Retrying in %.1fs ...",
                        self._name,
                        run_id,
                        job_id,
                        delay,
                    )
                    await self._sleep_or_shutdown(delay)
                    delay *= self._retry_backoff

            # All retries exhausted or fatal error
            error_msg: str = (
                f"Job '{job_id}' failed after {attempt} attempt(s)."
            )
            self._status = WorkerStatus.FAILED
            self._stats.failed_runs += 1
            self._stats.last_error = str(last_exception)

            self._logger.error(
                "Worker '%s' | Run '%s' | %s | Last error: %s",
                self._name,
                run_id,
                error_msg,
                last_exception,
            )

            # Lifecycle hook: on_failure
            await self._on_failure(job_id, last_exception, run_id)

            raise RuntimeError(error_msg) from last_exception

    async def shutdown(self) -> None:
        """Request a graceful shutdown of the worker."""
        self._logger.info(
            "Worker '%s' | Shutdown requested.", self._name
        )
        self._shutdown_event.set()

        if self._current_task is not None and not self._current_task.done():
            self._current_task.cancel()
            self._logger.debug(
                "Worker '%s' | Cancelled current task.", self._name
            )

    def get_status_report(self) -> dict[str, Any]:
        """Return a comprehensive status report for monitoring."""
        return {
            "worker": self._name,
            "version": self._version,
            "status": self._status.value,
            "is_shutdown_requested": self.is_shutdown_requested,
            "config": self._config_snapshot,
            "stats": self._stats.to_dict(),
        }

    # ------------------------------------------------------------------
    # Lifecycle Hooks
    # ------------------------------------------------------------------

    async def _on_start(
        self,
        job_id: str,
        payload: dict[str, Any] | None,
        run_id: str,
    ) -> None:
        """Hook called before execution begins.

        Override in subclasses to add pre-execution logic
        (e.g., resource acquisition, metrics increment).

        Args:
            job_id: Unique job identifier.
            payload: Optional input payload.
            run_id: Unique run identifier for this execution.
        """
        self._logger.debug(
            "Worker '%s' | Run '%s' | _on_start", self._name, run_id
        )

    async def _on_complete(
        self,
        job_id: str,
        result: dict[str, Any],
        run_id: str,
    ) -> None:
        """Hook called after successful execution.

        Override in subclasses to add post-execution logic
        (e.g., resource release, metrics update).

        Args:
            job_id: Unique job identifier.
            result: The result dictionary from execution.
            run_id: Unique run identifier for this execution.
        """
        self._logger.debug(
            "Worker '%s' | Run '%s' | _on_complete", self._name, run_id
        )

    async def _on_failure(
        self,
        job_id: str,
        exception: Exception | None,
        run_id: str,
    ) -> None:
        """Hook called when execution fails after all retries.

        Override in subclasses to add failure-handling logic
        (e.g., alerting, cleanup).

        Args:
            job_id: Unique job identifier.
            exception: The final exception that caused failure, or None.
            run_id: Unique run identifier for this execution.
        """
        self._logger.debug(
            "Worker '%s' | Run '%s' | _on_failure: %s",
            self._name,
            run_id,
            exception,
        )

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    async def _execute_with_timeout(
        self,
        job_id: str,
        payload: dict[str, Any] | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Wrap ``execute_async`` with timeout enforcement."""
        start_time: float = time.monotonic()

        self._current_task = asyncio.create_task(
            self.execute_async(job_id, payload)
        )

        try:
            result: dict[str, Any] = await asyncio.wait_for(
                self._current_task,
                timeout=self._timeout_seconds,
            )

            elapsed: float = time.monotonic() - start_time
            self._update_timing_stats(elapsed)

            return result

        except asyncio.TimeoutError:
            elapsed = time.monotonic() - start_time
            self._update_timing_stats(elapsed, is_timeout=True)
            raise

        except asyncio.CancelledError:
            elapsed = time.monotonic() - start_time
            self._update_timing_stats(elapsed)
            raise

        finally:
            self._current_task = None

    def _update_timing_stats(
        self,
        elapsed: float,
        is_timeout: bool = False,
    ) -> None:
        """Update execution timing statistics."""
        self._stats.last_execution_time = elapsed
        self._stats.last_run_at = time.time()
        self._stats.total_execution_time += elapsed

        if elapsed < self._stats.min_execution_time:
            self._stats.min_execution_time = elapsed
        if elapsed > self._stats.max_execution_time:
            self._stats.max_execution_time = elapsed

    async def _sleep_or_shutdown(self, duration: float) -> None:
        """
        Sleep for the given duration, but return early if a shutdown
        is requested.
        """
        try:
            await asyncio.wait_for(
                self._shutdown_event.wait(),
                timeout=duration,
            )
        except asyncio.TimeoutError:
            pass  # Normal timeout — sleep completed
