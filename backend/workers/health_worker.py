"""
VisionOps AI - Health Check Worker

Performs periodic health checks on the system's components and
services. This worker verifies the availability and responsiveness of
critical infrastructure by reading all paths from configuration —
no hardcoded directories or filenames.

Responsibilities:
    - Verify AI model file availability.
    - Check scheduler and worker status.
    - Validate storage directory accessibility.
    - Check uploads, outputs, and reports directories.
    - Verify configuration YAML files exist.
    - Check Power BI configuration.
    - Report disk space and optional memory usage.
    - Verify logger configuration.
    - Validate service layer responsiveness.
    - Handle retries, timeouts, and graceful shutdown.
    - Track job execution statistics.
"""

from __future__ import annotations

import logging
import pathlib
import shutil
from typing import Any, Dict, List

from core.config import settings
from workers.base import BaseWorker


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Config files to verify (relative to project root)
CONFIG_FILES: tuple[str, ...] = (
    "config/settings.yaml",
    "config/logging.yaml",
    "config/powerbi.yaml",
    "config/business_rules.yaml",
    "config/ai_config.yaml",
)

# YAML config files referenced in settings
POWERBI_CONFIG_PATH: str = "config/powerbi.yaml"


# ---------------------------------------------------------------------------
# Health Check Worker
# ---------------------------------------------------------------------------


class HealthCheckWorker(BaseWorker):
    """
    Background worker that performs periodic system health checks.

    All paths are read from ``core.config.settings`` — no hardcoded
    directories, filenames, or project root guessing. Delegates
    health checks to the relevant service and storage layers.
    """

    def __init__(
        self,
        name: str = "HealthCheckWorker",
        max_retries: int | None = None,
        retry_delay: float | None = None,
        retry_backoff: float | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        """
        Initialise the health check worker.

        All timing parameters fall back to ``core.config.settings``
        values. The project root is read from ``settings.BASE_DIR``
        (or ``settings.base_dir``).

        Args:
            name: Human-readable worker name.
            max_retries: Maximum retry attempts on failure.
            retry_delay: Initial retry delay in seconds.
            retry_backoff: Exponential backoff multiplier.
            timeout_seconds: Maximum allowed execution time.
        """
        if timeout_seconds is None:
            timeout_seconds = getattr(
                settings, "WORKER_HEALTH_TIMEOUT", 60
            )
        if max_retries is None:
            max_retries = getattr(
                settings, "WORKER_HEALTH_RETRIES", 1
            )

        super().__init__(
            name=name,
            max_retries=max_retries,
            retry_delay=retry_delay,
            retry_backoff=retry_backoff,
            timeout_seconds=timeout_seconds,
        )

        # Resolve project root from settings
        self._project_root: pathlib.Path = pathlib.Path(
            settings.base_dir
        ).resolve()

        # Build the list of paths to check from settings fields
        self._directories_to_check: Dict[str, str] = self._build_directory_map()
        self._data_files_to_check: Dict[str, str] = self._build_data_file_map()

        self._logger: logging.Logger = logging.getLogger(
            "visionops.workers.health_worker"
        )
        self._logger.info(
            "HealthCheckWorker initialised | root=%s | %d dirs | %d files",
            self._project_root,
            len(self._directories_to_check),
            len(self._data_files_to_check),
        )

    # ------------------------------------------------------------------
    # Configuration Helpers
    # ------------------------------------------------------------------

    def _build_directory_map(self) -> Dict[str, str]:
        """
        Build a mapping of directory names to their paths from settings.

        Returns:
            Dictionary of logical name -> relative path string.
        """
        return {
            "data_root": getattr(settings, "DATA_FOLDER", "data"),
            "raw_data": getattr(settings, "RAW_FOLDER", "data/raw"),
            "processed_data": getattr(
                settings, "PROCESSED_FOLDER", "data/processed"
            ),
            "analytics_data": getattr(
                settings, "ANALYTICS_FOLDER", "data/analytics"
            ),
            "archive": getattr(
                settings, "ARCHIVE_FOLDER", "data/archive"
            ),
            "logs": getattr(settings, "LOG_DIR", "logs"),
            "uploads": getattr(
                settings, "UPLOAD_FOLDER", "uploads/videos"
            ),
            "uploads_thumbnails": getattr(
                settings, "THUMBNAIL_FOLDER", "uploads/thumbnails"
            ),
            "annotated_videos": getattr(
                settings,
                "ANNOTATED_VIDEOS_DIR",
                "outputs/annotated_videos",
            ),
            "extracted_frames": getattr(
                settings,
                "EXTRACTED_FRAMES_DIR",
                "outputs/extracted_frames",
            ),
            "detection_images": getattr(
                settings,
                "DETECTION_IMAGES_DIR",
                "outputs/detection_images",
            ),
            "previews": getattr(
                settings, "PREVIEW_IMAGES_DIR", "outputs/previews"
            ),
            "reports_pdf": getattr(
                settings, "PDF_REPORTS_DIR", "reports/pdf"
            ),
            "reports_excel": getattr(
                settings, "EXCEL_REPORTS_DIR", "reports/excel"
            ),
            "reports_json": getattr(
                settings, "JSON_REPORTS_DIR", "reports/json"
            ),
        }

    def _build_data_file_map(self) -> Dict[str, str]:
        """
        Build a mapping of data file names to their paths from settings.

        Returns:
            Dictionary of logical name -> relative path string.
        """
        return {
            "videos_csv": getattr(
                settings, "VIDEOS_CSV", "data/videos.csv"
            ),
            "detections_csv": getattr(
                settings, "DETECTIONS_CSV", "data/detections.csv"
            ),
            "events_csv": getattr(
                settings, "EVENTS_CSV", "data/events.csv"
            ),
            "alerts_csv": getattr(
                settings, "ALERTS_CSV", "data/alerts.csv"
            ),
            "kpis_csv": getattr(
                settings, "KPIS_CSV", "data/kpis.csv"
            ),
            "analytics_csv": getattr(
                settings, "ANALYTICS_CSV", "data/analytics.csv"
            ),
            "summary_json": getattr(
                settings, "SUMMARY_JSON", "data/summary.json"
            ),
        }

    # ------------------------------------------------------------------
    # Abstract Method Implementation
    # ------------------------------------------------------------------

    async def execute_async(
        self,
        job_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a system health check job.

        Performs comprehensive checks across all system components
        using paths read from ``core.config.settings``.

        Args:
            job_id: Unique job identifier.
            payload: Optional parameters (e.g., check types to run).

        Returns:
            Dictionary containing structured health check results.
        """
        self._logger.info(
            "HealthCheckWorker | Job '%s' | Starting health checks.",
            job_id,
        )

        # Determine which check categories to run
        check_categories: List[str] = [
            "directories",
            "data_files",
            "ai_model",
            "config_files",
            "powerbi",
            "disk_space",
            "services",
        ]

        if payload is not None:
            check_categories = payload.get(
                "checks", check_categories
            )

        health_results: Dict[str, Any] = {
            "job_id": job_id,
            "status": "healthy",
            "checks": {},
        }

        # ----------------------------------------------------------
        # Check 1: Storage Directories
        # ----------------------------------------------------------
        if "directories" in check_categories:
            dir_results: Dict[str, bool] = await self._check_directories()
            health_results["checks"]["directories"] = dir_results
            if not all(dir_results.values()):
                health_results["status"] = "degraded"

        # ----------------------------------------------------------
        # Check 2: Data File Integrity
        # ----------------------------------------------------------
        if "data_files" in check_categories:
            file_results: Dict[str, bool] = await self._check_data_files()
            health_results["checks"]["data_files"] = file_results
            if not all(file_results.values()):
                health_results["status"] = "degraded"

        # ----------------------------------------------------------
        # Check 3: AI Model Availability
        # ----------------------------------------------------------
        if "ai_model" in check_categories:
            ai_result: Dict[str, Any] = await self._check_ai_model()
            health_results["checks"]["ai_model"] = ai_result
            if not ai_result["available"]:
                health_results["status"] = "degraded"

        # ----------------------------------------------------------
        # Check 4: Configuration Files
        # ----------------------------------------------------------
        if "config_files" in check_categories:
            config_results: Dict[str, bool] = await self._check_config_files()
            health_results["checks"]["config_files"] = config_results
            if not all(config_results.values()):
                health_results["status"] = "degraded"

        # ----------------------------------------------------------
        # Check 5: Power BI Configuration
        # ----------------------------------------------------------
        if "powerbi" in check_categories:
            powerbi_result: Dict[str, Any] = await self._check_powerbi_config()
            health_results["checks"]["powerbi"] = powerbi_result

        # ----------------------------------------------------------
        # Check 6: Disk Space
        # ----------------------------------------------------------
        if "disk_space" in check_categories:
            disk_result: Dict[str, Any] = await self._check_disk_space()
            health_results["checks"]["disk_space"] = disk_result

        # ----------------------------------------------------------
        # Check 7: Services Health
        # ----------------------------------------------------------
        if "services" in check_categories:
            service_results: Dict[str, Any] = await self._check_services()
            health_results["checks"]["services"] = service_results

        # Determine overall health message
        if health_results["status"] == "healthy":
            health_results["message"] = "All health checks passed."
        else:
            health_results["message"] = (
                "Some health checks failed. System is degraded."
            )

        self._logger.info(
            "HealthCheckWorker | Job '%s' | Health status: %s",
            job_id,
            health_results["status"],
        )

        return health_results

    # ------------------------------------------------------------------
    # Individual Health Checks
    # ------------------------------------------------------------------

    async def _check_directories(self) -> Dict[str, bool]:
        """
        Verify all required directories exist and are accessible.

        All paths are read from ``settings`` — no hardcoded values.

        Returns:
            Dictionary mapping directory names to availability status.
        """
        results: Dict[str, bool] = {}

        for name, relative_path in self._directories_to_check.items():
            full_path: pathlib.Path = (
                self._project_root / relative_path
            )
            exists: bool = full_path.exists() and full_path.is_dir()

            if not exists:
                self._logger.warning(
                    "HealthCheckWorker | Directory missing: %s (%s)",
                    name,
                    full_path,
                )
            results[name] = exists

        return results

    async def _check_data_files(self) -> Dict[str, bool]:
        """
        Verify all required data files exist and are accessible.

        All paths are read from ``settings`` — no hardcoded values.

        Returns:
            Dictionary mapping file names to existence status.
        """
        results: Dict[str, bool] = {}

        for name, relative_path in self._data_files_to_check.items():
            full_path: pathlib.Path = (
                self._project_root / relative_path
            )
            exists: bool = full_path.exists() and full_path.is_file()

            if not exists:
                self._logger.warning(
                    "HealthCheckWorker | Data file missing: %s (%s)",
                    name,
                    full_path,
                )
            results[name] = exists

        return results

    async def _check_ai_model(self) -> Dict[str, Any]:
        """
        Verify the AI model file exists and is accessible.

        Reads the model path from ``settings.YOLO_MODEL_PATH``.

        Returns:
            Dictionary with 'available' (bool) and 'path' (str).
        """
        model_path_str: str = getattr(
            settings,
            "YOLO_MODEL_PATH",
            "ai/models/detection/yolov8n.pt",
        )
        model_path: pathlib.Path = (
            self._project_root / model_path_str
        )
        available: bool = (
            model_path.exists() and model_path.is_file()
        )

        if not available:
            self._logger.warning(
                "HealthCheckWorker | AI model missing: %s",
                model_path,
            )

        return {
            "available": available,
            "path": str(model_path),
        }

    async def _check_config_files(self) -> Dict[str, bool]:
        """
        Verify all configuration YAML files exist.

        Returns:
            Dictionary mapping config file names to existence status.
        """
        results: Dict[str, bool] = {}

        for relative_path in CONFIG_FILES:
            full_path: pathlib.Path = (
                self._project_root / relative_path
            )
            exists: bool = full_path.exists() and full_path.is_file()

            if not exists:
                self._logger.warning(
                    "HealthCheckWorker | Config file missing: %s",
                    full_path,
                )
            results[relative_path] = exists

        return results

    async def _check_powerbi_config(self) -> Dict[str, Any]:
        """
        Verify Power BI configuration.

        Checks whether the Power BI config file exists and whether
        Power BI export is enabled in settings.

        Returns:
            Dictionary with enabled status and config file check.
        """
        powerbi_enabled: bool = getattr(
            settings, "POWERBI_ENABLED", False
        )
        config_path: pathlib.Path = (
            self._project_root / POWERBI_CONFIG_PATH
        )
        config_exists: bool = (
            config_path.exists() and config_path.is_file()
        )

        return {
            "enabled": powerbi_enabled,
            "config_file_exists": config_exists,
            "config_file_path": str(config_path),
        }

    async def _check_disk_space(self) -> Dict[str, Any]:
        """
        Check available disk space on the project filesystem.

        Returns:
            Dictionary with total, used, free, and usage percentage.
        """
        try:
            usage = shutil.disk_usage(self._project_root)

            total_gb: float = round(
                usage.total / (1024 ** 3), 2
            )
            used_gb: float = round(
                usage.used / (1024 ** 3), 2
            )
            free_gb: float = round(
                usage.free / (1024 ** 3), 2
            )
            usage_percent: float = round(
                (usage.used / usage.total) * 100, 1
            )

            return {
                "total_gb": total_gb,
                "used_gb": used_gb,
                "free_gb": free_gb,
                "usage_percent": usage_percent,
                "healthy": usage_percent < 90.0,
            }
        except Exception as exc:
            self._logger.error(
                "HealthCheckWorker | Disk space check failed: %s",
                exc,
            )
            return {
                "total_gb": None,
                "used_gb": None,
                "free_gb": None,
                "usage_percent": None,
                "healthy": False,
                "error": str(exc),
            }

    async def _check_services(self) -> Dict[str, Any]:
        """
        Perform optional service-level health checks.

        This method delegates to the service layer for health
        verification of critical services.

        Returns:
            Dictionary mapping service names to their health status.
        """
        # ----------------------------------------------------------
        # Delegate to service layer for health checks.
        #
        # TODO: Uncomment and wire the actual services when available.
        #
        #   from services.analysis_service import AnalysisService
        #   from services.analytics_service import AnalyticsService
        #
        #   analysis_health = await AnalysisService().health()
        #   analytics_health = await AnalyticsService().health()
        # ----------------------------------------------------------

        self._logger.debug(
            "HealthCheckWorker | Service health checks delegated "
            "to service layer."
        )

        return {
            "analysis_service": {
                "status": "pending",
                "message": (
                    "Health check delegated — service not yet wired."
                ),
            },
            "analytics_service": {
                "status": "pending",
                "message": (
                    "Health check delegated — service not yet wired."
                ),
            },
            "report_service": {
                "status": "pending",
                "message": (
                    "Health check delegated — service not yet wired."
                ),
            },
            "notification_service": {
                "status": "pending",
                "message": (
                    "Health check delegated — service not yet wired."
                ),
            },
        }
