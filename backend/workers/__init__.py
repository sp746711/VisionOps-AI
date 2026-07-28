"""
VisionOps AI - Workers Package

Provides background worker implementations and the scheduler manager
for coordinating recurring and one-off background jobs.

All workers in this package follow a common contract defined by the
``BaseWorker`` abstract class in ``workers.base``. They coordinate
with existing service layers and do NOT contain business logic, AI
algorithms, or API endpoints.

Exports:
    - BaseWorker             Abstract base class for all workers.
    - WorkerStatus           Enumeration of worker lifecycle states.
    - ExecutionStats         Data class for execution statistics.
    - ExecutionRecord        Data class for scheduled job execution history.
    - SchedulerManager       APScheduler-based job scheduler with cron support.
    - ScheduledJob           Data class for registered scheduled jobs.
    - VideoProcessingWorker  Coordinates video processing jobs.
    - AnalyticsWorker        Coordinates analytics processing jobs.
    - ReportGenerationWorker Coordinates report generation jobs.
    - CleanupWorker          Coordinates system cleanup jobs.
    - AlertWorker            Coordinates alert evaluation jobs.
    - HealthCheckWorker      Coordinates system health checks.
    - PowerBIExportWorker    Coordinates Power BI dataset exports.
"""

from __future__ import annotations

from workers.base import BaseWorker, ExecutionStats, WorkerStatus
from workers.scheduler import (
    SchedulerManager,
    ScheduledJob,
    ExecutionRecord,
)
from workers.video_worker import VideoProcessingWorker
from workers.analytics_worker import AnalyticsWorker
from workers.report_worker import ReportGenerationWorker
from workers.cleanup_worker import CleanupWorker
from workers.alert_worker import AlertWorker
from workers.health_worker import HealthCheckWorker
from workers.powerbi_worker import PowerBIExportWorker

__all__: list[str] = [
    # Base
    "BaseWorker",
    "WorkerStatus",
    "ExecutionStats",
    # Scheduler
    "SchedulerManager",
    "ScheduledJob",
    "ExecutionRecord",
    # Workers
    "VideoProcessingWorker",
    "AnalyticsWorker",
    "ReportGenerationWorker",
    "CleanupWorker",
    "AlertWorker",
    "HealthCheckWorker",
    "PowerBIExportWorker",
]
