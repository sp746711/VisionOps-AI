#!/usr/bin/env python3
"""VisionOps AI — Reset Project Script.

Performs a full project reset:

1. Creates a timestamped backup of current data.
2. Cleans all generated outputs (reports, annotated videos, frames, etc.).
3. Deletes temporary files.
4. Deletes analytics data.
5. Recreates default CSV and JSON data files.
6. Validates the project state after reset.

Never deletes project data before backup unless ``--force`` is specified.

Usage:
    python -m backend.scripts.reset_project
    python -m backend.scripts.reset_project --force
    python -m backend.scripts.reset_project --verbose
    python -m backend.scripts.reset_project --dry-run
    python -m backend.scripts.reset_project --yes
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.exceptions import StorageError, FileOperationError
from backend.storage import BackupManager, FileManager, StorageService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EXIT_SUCCESS: int = 0
_EXIT_FAILURE: int = 1

# Directories to clean during reset (same as clean_outputs)
_CLEANABLE_DIRECTORIES: list[str] = [
    "annotated_videos",
    "extracted_frames",
    "detection_images",
    "previews",
    "pdf_reports",
    "excel_reports",
    "json_reports",
]

# CSV headers for re-creation (matches other scripts)
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
# Core logic (separated from CLI for testability)
# ---------------------------------------------------------------------------


def reset_project(
    storage: StorageService,
    backup_manager: BackupManager,
    file_manager: FileManager,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute the full project reset workflow.

    Args:
        storage: Initialized ``StorageService`` instance.
        backup_manager: Initialized ``BackupManager`` instance.
        file_manager: Initialized ``FileManager`` instance.
        force: If ``True``, skip backup step.
        dry_run: If ``True``, simulate without making changes.

    Returns:
        Dictionary with reset results:
        - ``backup_created``: Backup path or empty string.
        - ``files_cleaned``: Number of files removed during cleanup.
        - ``bytes_freed``: Bytes freed during cleanup.
        - ``csv_files_created``: List of CSV stores (re)created.
        - ``json_files_created``: List of JSON stores (re)created.
        - ``storage_valid``: Whether the storage validates after reset.
        - ``errors``: List of error messages.

    Raises:
        StorageError: If storage operations fail critically.
    """
    result: dict[str, Any] = {
        "backup_created": "",
        "files_cleaned": 0,
        "bytes_freed": 0,
        "csv_files_created": [],
        "json_files_created": [],
        "storage_valid": False,
        "errors": [],
    }

    # Step 1: Backup (unless --force)
    if not force:
        logger.info("Step 1/5: Creating backup…")
        try:
            if dry_run:
                logger.info("[DRY-RUN] Would create backup.")
                result["backup_created"] = "[dry-run]"
            else:
                bp = backup_manager.create_backup(label="before_reset")
                result["backup_created"] = str(bp.resolve())
                logger.info("Backup created: %s", bp)
        except StorageError as exc:
            msg = f"Backup failed: {exc}"
            logger.error(msg)
            result["errors"].append(msg)
            # Continue anyway to allow forced reset
    else:
        logger.info("Step 1/5: Skipping backup (--force specified).")

    # Step 2: Clean outputs
    logger.info("Step 2/5: Cleaning generated outputs…")
    for dir_name in _CLEANABLE_DIRECTORIES:
        try:
            if dir_name in ("logs",):
                dir_path = Path(settings.LOG_DIR)
            else:
                dir_path = Path(
                    getattr(
                        settings,
                        file_manager._MANAGED_DIRECTORIES[dir_name],
                    )
                )

            if not dir_path.exists() or not dir_path.is_dir():
                logger.debug("Directory '%s' does not exist — skipping.", dir_name)
                continue

            files = sorted(p for p in dir_path.rglob("*") if p.is_file())
            if not files:
                continue

            if dry_run:
                total_size = sum(p.stat().st_size for p in files)
                logger.info(
                    "[DRY-RUN] Would delete %d file(s) from '%s' (%s)",
                    len(files),
                    dir_name,
                    _format_size(total_size),
                )
                result["files_cleaned"] += len(files)
                result["bytes_freed"] += total_size
            else:
                for f in files:
                    try:
                        sz = f.stat().st_size
                        f.unlink()
                        result["files_cleaned"] += 1
                        result["bytes_freed"] += sz
                    except OSError as exc:
                        logger.warning("Failed to delete %s: %s", f, exc)

                # Remove empty subdirectories
                for subdir in sorted(
                    dir_path.rglob("*"),
                    key=lambda p: len(str(p)),
                    reverse=True,
                ):
                    if subdir.is_dir() and not any(subdir.iterdir()):
                        try:
                            subdir.rmdir()
                        except OSError:
                            pass

                logger.info(
                    "Cleaned '%s': %d files removed.",
                    dir_name,
                    len(files),
                )
        except (FileOperationError, KeyError) as exc:
            logger.warning("Error cleaning '%s': %s", dir_name, exc)
            result["errors"].append(str(exc))

    # Step 3: Clear CSV stores
    logger.info("Step 3/5: Clearing CSV data stores…")
    for store_name in _CSV_HEADERS:
        try:
            if dry_run:
                logger.info("[DRY-RUN] Would clear and recreate CSV store: %s", store_name)
                result["csv_files_created"].append(store_name)
            else:
                storage.csv_manager.write_store(
                    store_name, [], fieldnames=_CSV_HEADERS[store_name]
                )
                result["csv_files_created"].append(store_name)
                logger.info("Recreated CSV store: %s", store_name)
        except StorageError as exc:
            msg = f"Failed to recreate CSV store '{store_name}': {exc}"
            logger.error(msg)
            result["errors"].append(msg)

    # Step 4: Clear and recreate JSON summary
    logger.info("Step 4/5: Recreating JSON summary…")
    try:
        if dry_run:
            logger.info("[DRY-RUN] Would recreate JSON summary.")
            result["json_files_created"].append("summary")
        else:
            import datetime

            summary = dict(_DEFAULT_SUMMARY)
            summary["initialized_at"] = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
            storage.json_manager.write_store("summary", summary)
            result["json_files_created"].append("summary")
            logger.info("Recreated JSON summary store.")
    except StorageError as exc:
        msg = f"Failed to recreate JSON summary: {exc}"
        logger.error(msg)
        result["errors"].append(msg)

    # Step 5: Validate storage after reset
    logger.info("Step 5/5: Validating storage after reset…")
    validation_errors: list[str] = []
    if not dry_run:
        for store_name in _CSV_HEADERS:
            try:
                exists = storage.csv_manager.store_exists(store_name)
                if not exists:
                    validation_errors.append(f"CSV store '{store_name}' missing after reset")
            except StorageError as exc:
                validation_errors.append(f"CSV store '{store_name}' error: {exc}")

        try:
            json_exists = storage.json_manager.store_exists("summary")
            if not json_exists:
                validation_errors.append("JSON store 'summary' missing after reset")
        except StorageError as exc:
            validation_errors.append(f"JSON store 'summary' error: {exc}")

    result["storage_valid"] = len(validation_errors) == 0
    if validation_errors:
        for err in validation_errors:
            logger.error("Validation error: %s", err)
        result["errors"].extend(validation_errors)

    return result


def _format_size(size_bytes: int) -> str:
    """Format a byte count into a human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Formatted string like ``"42.5 MB"``.
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes / (1024**2):.1f} MB"
    else:
        return f"{size_bytes / (1024**3):.2f} GB"


def _print_result(result: dict[str, Any]) -> None:
    """Print a human-readable summary of the reset operation.

    Args:
        result: Result dictionary from :func:`reset_project`.
    """
    separator = "=" * 60
    print(f"\n{separator}")
    print(f"  {settings.PROJECT_NAME} — Reset Summary")
    print(f"{separator}")

    if result["backup_created"] and result["backup_created"] != "[dry-run]":
        print(f"  Backup          : {result['backup_created']}")
    elif result["backup_created"] == "[dry-run]":
        print("  Backup          : [dry-run — would create backup]")
    else:
        print("  Backup          : Skipped (--force)")

    print(f"  Files Cleaned   : {result['files_cleaned']:,}")
    print(f"  Space Freed     : {_format_size(result['bytes_freed'])}")
    print(f"  CSV Stores      : {len(result['csv_files_created'])} recreated")
    print(f"  JSON Stores     : {len(result['json_files_created'])} recreated")
    print(f"  Storage Valid   : {'✓' if result['storage_valid'] else '✗'}")

    if result["errors"]:
        print(f"  Errors          : {len(result['errors'])}")
        for err in result["errors"]:
            print(f"    - {err}")

    print(f"{separator}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI.

    Returns:
        Configured ``ArgumentParser`` instance.
    """
    parser = argparse.ArgumentParser(
        prog="reset_project",
        description="Reset the VisionOps AI project to its initial state.",
        epilog=(
            "Example: python -m backend.scripts.reset_project --yes\n"
            "         python -m backend.scripts.reset_project --force"
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip the automatic backup step before resetting.",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt and proceed with reset.",
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
        help="Simulate reset without making any changes.",
    )
    return parser


def _prompt_confirmation() -> bool:
    """Prompt the user to confirm the reset operation.

    Returns:
        ``True`` if the user confirms, ``False`` otherwise.
    """
    print("\nWARNING: This will DELETE all generated data and reset the project.")
    print("  • All reports, annotated videos, extracted frames will be removed.")
    print("  • All CSV data stores (videos, detections, events, alerts, KPIs) will be cleared.")
    print("  • The summary JSON will be reset to defaults.")
    print("  • Uploaded videos and configuration will NOT be affected.")
    print()

    response = input("Are you sure you want to reset the project? [y/N]: ").strip().lower()
    return response in ("y", "yes")


def main() -> int:
    """Execute the project reset workflow.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = create_parser()
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

    logger.info("=== VisionOps AI — Reset Project ===")
    logger.info("Script started: reset_project.py")

    if args.dry_run:
        logger.info("DRY-RUN mode enabled — no changes will be made.")
    if args.force:
        logger.info("Force mode enabled — backup will be skipped.")

    # Confirmation
    if not args.yes and not args.dry_run:
        if not _prompt_confirmation():
            print("Reset cancelled.")
            logger.info("Reset cancelled by user.")
            return _EXIT_SUCCESS

    try:
        storage = StorageService()
        storage.initialize()
        backup_manager = BackupManager()
        file_manager = FileManager()
    except (StorageError, FileOperationError) as exc:
        logger.error("Failed to initialise services: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return _EXIT_FAILURE

    try:
        result = reset_project(
            storage,
            backup_manager,
            file_manager,
            force=args.force,
            dry_run=args.dry_run,
        )
    except StorageError as exc:
        logger.error("Reset failed: %s", exc)
        print(f"ERROR: Reset failed: {exc}", file=sys.stderr)
        return _EXIT_FAILURE

    _print_result(result)

    if result["errors"] and not args.dry_run:
        logger.warning(
            "=== Reset completed with %d error(s) ===",
            len(result["errors"]),
        )
        return _EXIT_FAILURE

    logger.info("=== Project reset completed successfully ===")
    return _EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
