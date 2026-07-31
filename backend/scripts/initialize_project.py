#!/usr/bin/env python3
"""VisionOps AI — Project Initialization Script.

Validates the runtime environment, initializes the storage layer, creates
default data files (CSV headers + JSON summary), and prints a summary of
the project state.

Usage:
    python -m backend.scripts.initialize_project
    python -m backend.scripts.initialize_project --verbose
    python -m backend.scripts.initialize_project --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.exceptions import VisionOpsError, StorageError
from backend.storage import StorageService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_PYTHON_VERSION: tuple[int, int] = (3, 12)
_EXIT_SUCCESS: int = 0
_EXIT_FAILURE: int = 1

# CSV headers for each data store (matching the models used by services)
_CSV_HEADERS: dict[str, list[str]] = {
    "videos": [
        "video_id",
        "filename",
        "file_size",
        "content_type",
        "status",
        "error_message",
        "created_at",
        "updated_at",
        "processing_started_at",
        "processing_completed_at",
        "duration_seconds",
        "total_frames",
        "fps",
        "thumbnail_path",
        "annotated_path",
    ],
    "detections": [
        "detection_id",
        "video_id",
        "frame_number",
        "class_name",
        "confidence",
        "bbox_x",
        "bbox_y",
        "bbox_w",
        "bbox_h",
        "track_id",
        "created_at",
    ],
    "events": [
        "event_id",
        "video_id",
        "event_type",
        "description",
        "severity",
        "source",
        "created_at",
        "updated_at",
    ],
    "alerts": [
        "alert_id",
        "video_id",
        "severity",
        "message",
        "acknowledged",
        "acknowledged_at",
        "acknowledged_by",
        "escalated",
        "escalation_level",
        "source",
        "created_at",
        "updated_at",
    ],
    "kpis": [
        "kpi_id",
        "video_id",
        "metric",
        "value",
        "unit",
        "timestamp",
    ],
    "analytics": [
        "analytics_id",
        "video_id",
        "metric",
        "value",
        "unit",
        "period_start",
        "period_end",
        "created_at",
    ],
}

# Default summary JSON structure
_DEFAULT_SUMMARY: dict[str, Any] = {
    "project": settings.PROJECT_NAME,
    "version": settings.VERSION,
    "environment": settings.ENVIRONMENT,
    "initialized_at": "",
    "total_videos": 0,
    "total_detections": 0,
    "total_events": 0,
    "total_alerts": 0,
    "total_kpis": 0,
    "videos": {},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_python_version() -> None:
    """Validate that the Python version meets the minimum requirement.

    Raises:
        SystemExit: If Python version is below 3.12.
    """
    current = sys.version_info[:2]
    if current < _MIN_PYTHON_VERSION:
        msg = (
            f"Python {_MIN_PYTHON_VERSION[0]}.{_MIN_PYTHON_VERSION[1]} "
            f"or higher is required. Current: {current[0]}.{current[1]}"
        )
        logger.critical(msg)
        print(f"ERROR: {msg}", file=sys.stderr)
        sys.exit(_EXIT_FAILURE)
    logger.info("Python version validated: %s.%s", current[0], current[1])


def _validate_environment() -> None:
    """Validate that the application environment is correctly configured.

    Logs warnings for production environments with debug mode enabled.
    """
    env = settings.ENVIRONMENT
    logger.info("Environment: %s (debug=%s)", env.upper(), settings.DEBUG)

    if settings.is_production() and settings.DEBUG:
        logger.warning("DEBUG mode is enabled in PRODUCTION — disable for security.")


def _validate_configuration() -> None:
    """Validate critical configuration values.

    Raises:
        SystemExit: If critical configuration is invalid.
    """
    errors: list[str] = []

    if settings.is_production():
        secret = settings.SECRET_KEY
        if secret in ("change-me", "change-me-to-a-secure-random-secret-key-in-production"):
            errors.append("SECRET_KEY must be changed from default in production.")

    if not settings.ALLOWED_VIDEO_EXTENSIONS:
        errors.append("ALLOWED_VIDEO_EXTENSIONS must not be empty.")

    if settings.UPLOAD_MAX_SIZE < 1:
        errors.append("UPLOAD_MAX_SIZE must be greater than 0.")

    if errors:
        for err in errors:
            logger.error("Configuration error: %s", err)
            print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(_EXIT_FAILURE)

    logger.info("Configuration validated successfully.")


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def _collect_store_info(
    storage: StorageService,
) -> dict[str, Any]:
    """Collect metadata about all CSV and JSON data stores.

    Args:
        storage: Initialized StorageService instance.

    Returns:
        Dictionary with keys ``csv_stores`` and ``json_stores``.
    """
    csv_stores: list[dict[str, Any]] = []
    for name in storage.csv_manager.store_names():
        try:
            info = storage.csv_manager.store_info(name)
            # Check if headers are present
            if info["exists"]:
                try:
                    headers = storage.csv_manager.check_headers(
                        name, _CSV_HEADERS.get(name, [])
                    )
                    info["headers_valid"] = headers
                except (StorageError, FileNotFoundError):
                    info["headers_valid"] = False
            else:
                info["headers_valid"] = False
            csv_stores.append(info)
        except StorageError as exc:
            logger.warning("Failed to collect info for CSV store '%s': %s", name, exc)
            csv_stores.append({"name": name, "error": str(exc)})

    json_stores: list[dict[str, Any]] = []
    for name in storage.json_manager.store_names():
        try:
            info = storage.json_manager.store_info(name)
            json_stores.append(info)
        except StorageError as exc:
            logger.warning("Failed to collect info for JSON store '%s': %s", name, exc)
            json_stores.append({"name": name, "error": str(exc)})

    return {"csv_stores": csv_stores, "json_stores": json_stores}


def _print_summary(
    storage: StorageService,
    store_info: dict[str, Any],
) -> None:
    """Print a human-readable initialization summary to stdout.

    Args:
        storage: Initialized StorageService instance.
        store_info: Store metadata from :func:`_collect_store_info`.
    """
    separator = "=" * 60
    print(f"\n{separator}")
    print(f"  {settings.PROJECT_NAME} — Initialization Summary")
    print(f"{separator}")
    print(f"  Version      : {settings.VERSION}")
    print(f"  Environment  : {settings.ENVIRONMENT.upper()}")
    print(f"  Python       : {sys.version.split()[0]}")
    print(f"  Project Root : {settings.base_dir}")
    print()

    # Managed directories
    print("  Managed Directories:")
    dirs = storage.file_manager.list_managed_directories()
    for name, path in sorted(dirs.items()):
        exists = "✓" if path.is_dir() else "✗"
        print(f"    {exists} {name:25s} {path}")

    print()

    # CSV stores
    print("  CSV Data Stores:")
    for info in store_info["csv_stores"]:
        name = info.get("name", "?")
        exists = info.get("exists", False)
        size = info.get("size_bytes")
        headers = info.get("headers_valid", False)
        status = "✓" if exists and headers else ("⚠" if exists else "✗")
        size_str = f"({size:,} bytes)" if size is not None else "(empty)"
        print(f"    {status} {name:15s} {size_str:>15s}")

    print()

    # JSON stores
    print("  JSON Data Stores:")
    for info in store_info["json_stores"]:
        name = info.get("name", "?")
        exists = info.get("exists", False)
        size = info.get("size_bytes")
        status = "✓" if exists else "✗"
        size_str = f"({size:,} bytes)" if size is not None else "(empty)"
        print(f"    {status} {name:15s} {size_str:>15s}")

    print(f"{separator}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI.

    Returns:
        Configured ``ArgumentParser`` instance.
    """
    parser = argparse.ArgumentParser(
        prog="initialize_project",
        description="Initialize the VisionOps AI project environment.",
        epilog="Example: python -m backend.scripts.initialize_project --verbose",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose (DEBUG) logging output.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate initialization without making any changes.",
    )
    return parser


def main() -> int:
    """Execute the project initialization workflow.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = create_parser()
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Logging setup
    # ------------------------------------------------------------------
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    logger.info("=== VisionOps AI Project Initialization ===")
    logger.info("Script started: initialize_project.py")

    if args.dry_run:
        logger.info("DRY-RUN mode enabled — no changes will be made.")

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    logger.info("Validating environment…")
    _validate_python_version()
    _validate_environment()
    _validate_configuration()

    # ------------------------------------------------------------------
    # Storage initialization
    # ------------------------------------------------------------------
    logger.info("Initializing storage layer…")
    try:
        storage = StorageService()
        if not args.dry_run:
            directories = storage.initialize()
            logger.info("Storage layer initialized: %d directories", len(directories))
        else:
            logger.info("[DRY-RUN] Would initialize StorageService.")
    except StorageError as exc:
        logger.error("Storage initialization failed: %s", exc)
        print(f"ERROR: Storage initialization failed: {exc}", file=sys.stderr)
        return _EXIT_FAILURE

    # ------------------------------------------------------------------
    # Create default CSV files with headers
    # ------------------------------------------------------------------
    if not args.dry_run:
        for store_name, headers in _CSV_HEADERS.items():
            try:
                if not storage.csv_manager.store_exists(store_name):
                    storage.csv_manager.write_store(store_name, [], fieldnames=headers)
                    logger.info("Created default CSV store: %s (%d columns)", store_name, len(headers))
                else:
                    logger.debug("CSV store already exists: %s", store_name)
            except StorageError as exc:
                logger.warning("Failed to create CSV store '%s': %s", store_name, exc)
    else:
        for store_name in _CSV_HEADERS:
            logger.info("[DRY-RUN] Would create CSV store: %s", store_name)

    # ------------------------------------------------------------------
    # Create default JSON summary
    # ------------------------------------------------------------------
    if not args.dry_run:
        try:
            if not storage.json_manager.store_exists("summary"):
                import datetime
                _DEFAULT_SUMMARY["initialized_at"] = datetime.datetime.now(
                    datetime.timezone.utc
                ).isoformat()
                storage.json_manager.write_store("summary", _DEFAULT_SUMMARY)
                logger.info("Created default JSON summary store.")
            else:
                logger.debug("JSON summary already exists.")
        except StorageError as exc:
            logger.warning("Failed to create JSON summary: %s", exc)
    else:
        logger.info("[DRY-RUN] Would create default JSON summary.")

    # ------------------------------------------------------------------
    # Collect and display summary
    # ------------------------------------------------------------------
    store_info = _collect_store_info(storage)
    _print_summary(storage, store_info)

    logger.info("=== Project initialization completed successfully ===")
    return _EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
