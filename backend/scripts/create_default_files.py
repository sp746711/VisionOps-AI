#!/usr/bin/env python3
"""VisionOps AI — Create Default Data Files.

Creates default CSV data-store files with proper headers and a default
JSON summary file if they do not already exist.  Existing files are
preserved unless ``--force`` is specified.

Usage:
    python -m backend.scripts.create_default_files
    python -m backend.scripts.create_default_files --force
    python -m backend.scripts.create_default_files --verbose
    python -m backend.scripts.create_default_files --dry-run
"""

from __future__ import annotations

import argparse
import datetime
import logging
import sys
from typing import Any

from backend.core.config import settings
from backend.exceptions import StorageError
from backend.storage import StorageService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EXIT_SUCCESS: int = 0
_EXIT_FAILURE: int = 1

# CSV headers matching the services layer expectations
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


def create_default_files(
    storage: StorageService,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create default data files if they do not exist.

    Args:
        storage: Initialized ``StorageService`` instance.
        force: If ``True``, overwrite existing files.
        dry_run: If ``True``, simulate without writing.

    Returns:
        Dictionary summarizing created files:
        - ``csv_files_created``: List of CSV store names created.
        - ``csv_files_skipped``: List of CSV store names already existing.
        - ``csv_files_overwritten``: List of CSV store names overwritten.
        - ``json_files_created``: List of JSON store names created.
        - ``json_files_skipped``: List of JSON store names already existing.
        - ``json_files_overwritten``: List of JSON store names overwritten.

    Raises:
        StorageError: If a write operation fails.
    """
    result: dict[str, Any] = {
        "csv_files_created": [],
        "csv_files_skipped": [],
        "csv_files_overwritten": [],
        "json_files_created": [],
        "json_files_skipped": [],
        "json_files_overwritten": [],
    }

    # --- CSV files ---
    for store_name, headers in _CSV_HEADERS.items():
        exists = storage.csv_manager.store_exists(store_name)

        if exists and not force:
            logger.info("CSV store '%s' already exists — skipping.", store_name)
            result["csv_files_skipped"].append(store_name)
            continue

        if dry_run:
            action = "overwrite" if exists else "create"
            logger.info("[DRY-RUN] Would %s CSV store: %s", action, store_name)
            if exists:
                result["csv_files_overwritten"].append(store_name)
            else:
                result["csv_files_created"].append(store_name)
            continue

        try:
            storage.csv_manager.write_store(store_name, [], fieldnames=headers)
            if exists:
                logger.info("Overwritten CSV store: %s (%d columns)", store_name, len(headers))
                result["csv_files_overwritten"].append(store_name)
            else:
                logger.info("Created CSV store: %s (%d columns)", store_name, len(headers))
                result["csv_files_created"].append(store_name)
        except StorageError as exc:
            logger.error("Failed to write CSV store '%s': %s", store_name, exc)
            raise

    # --- JSON files ---
    json_store_name = "summary"
    exists = storage.json_manager.store_exists(json_store_name)

    if exists and not force:
        logger.info("JSON store '%s' already exists — skipping.", json_store_name)
        result["json_files_skipped"].append(json_store_name)
    elif dry_run:
        action = "overwrite" if exists else "create"
        logger.info("[DRY-RUN] Would %s JSON store: %s", action, json_store_name)
        if exists:
            result["json_files_overwritten"].append(json_store_name)
        else:
            result["json_files_created"].append(json_store_name)
    else:
        try:
            summary = dict(_DEFAULT_SUMMARY)
            summary["initialized_at"] = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
            storage.json_manager.write_store(json_store_name, summary)
            if exists:
                logger.info("Overwritten JSON store: %s", json_store_name)
                result["json_files_overwritten"].append(json_store_name)
            else:
                logger.info("Created JSON store: %s", json_store_name)
                result["json_files_created"].append(json_store_name)
        except StorageError as exc:
            logger.error("Failed to write JSON store '%s': %s", json_store_name, exc)
            raise

    return result


def _print_result(result: dict[str, Any]) -> None:
    """Print a human-readable summary of created files.

    Args:
        result: Result dictionary from :func:`create_default_files`.
    """
    separator = "=" * 60
    print(f"\n{separator}")
    print(f"  {settings.PROJECT_NAME} — Default Files Summary")
    print(f"{separator}")

    created = result["csv_files_created"]
    skipped = result["csv_files_skipped"]
    overwritten = result["csv_files_overwritten"]

    print(f"\n  CSV Files: {len(created)} created, {len(overwritten)} overwritten, {len(skipped)} skipped")
    if created:
        print(f"    Created    : {', '.join(created)}")
    if overwritten:
        print(f"    Overwritten: {', '.join(overwritten)}")
    if skipped:
        print(f"    Skipped    : {', '.join(skipped)}")

    json_created = result["json_files_created"]
    json_skipped = result["json_files_skipped"]
    json_overwritten = result["json_files_overwritten"]

    print(f"\n  JSON Files: {len(json_created)} created, {len(json_overwritten)} overwritten, {len(json_skipped)} skipped")
    if json_created:
        print(f"    Created    : {', '.join(json_created)}")
    if json_overwritten:
        print(f"    Overwritten: {', '.join(json_overwritten)}")
    if json_skipped:
        print(f"    Skipped    : {', '.join(json_skipped)}")

    total = len(created) + len(json_created) + len(overwritten) + len(json_overwritten)
    print(f"\n  Total files written: {total}")
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
        prog="create_default_files",
        description="Create default CSV and JSON data files for VisionOps AI.",
        epilog="Example: python -m backend.scripts.create_default_files --force",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite existing files if they already exist.",
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
        help="Simulate without making any changes.",
    )
    return parser


def main() -> int:
    """Execute the default file creation workflow.

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

    logger.info("=== VisionOps AI — Create Default Files ===")
    logger.info("Script started: create_default_files.py")

    if args.force:
        logger.info("Force mode enabled — existing files will be overwritten.")
    if args.dry_run:
        logger.info("DRY-RUN mode enabled — no changes will be made.")

    try:
        storage = StorageService()
        storage.initialize()
    except StorageError as exc:
        logger.error("Storage initialization failed: %s", exc)
        print(f"ERROR: Storage initialization failed: {exc}", file=sys.stderr)
        return _EXIT_FAILURE

    try:
        result = create_default_files(
            storage,
            force=args.force,
            dry_run=args.dry_run,
        )
    except StorageError as exc:
        logger.error("Failed to create default files: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return _EXIT_FAILURE

    # Validate created files
    logger.info("Validating created files…")
    validation_errors: list[str] = []
    for store_name in _CSV_HEADERS:
        exists = storage.csv_manager.store_exists(store_name)
        if not exists:
            validation_errors.append(f"CSV store '{store_name}' missing after creation")

    json_exists = storage.json_manager.store_exists("summary")
    if not json_exists:
        validation_errors.append("JSON store 'summary' missing after creation")

    if validation_errors:
        for err in validation_errors:
            logger.error("Validation error: %s", err)
        print(f"ERROR: {len(validation_errors)} validation error(s)", file=sys.stderr)

    _print_result(result)

    if validation_errors:
        logger.warning("=== Default files created with %d validation error(s) ===", len(validation_errors))
        return _EXIT_FAILURE

    logger.info("=== Default files created successfully ===")
    return _EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
