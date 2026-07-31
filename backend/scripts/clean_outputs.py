#!/usr/bin/env python3
"""VisionOps AI — Clean Outputs Script.

Removes generated artifacts from output directories while preserving
source data, uploads, configuration, and model files.

Cleaned directories:
    - reports/ (pdf, excel, json)
    - outputs/annotated_videos/
    - outputs/extracted_frames/
    - outputs/detection_images/
    - outputs/previews/
    - logs/ (optional)

Preserved directories (never cleaned):
    - uploads/
    - data/ (CSV stores, JSON stores)
    - config/
    - models/
    - exceptions/

Usage:
    python -m backend.scripts.clean_outputs
    python -m backend.scripts.clean_outputs --confirm
    python -m backend.scripts.clean_outputs --verbose
    python -m backend.scripts.clean_outputs --dry-run
    python -m backend.scripts.clean_outputs --include-logs
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.exceptions import FileOperationError, StorageError
from backend.storage import FileManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EXIT_SUCCESS: int = 0
_EXIT_FAILURE: int = 1

# Output directories that can be safely cleaned
_CLEANABLE_DIRECTORIES: list[str] = [
    "annotated_videos",
    "extracted_frames",
    "detection_images",
    "previews",
    "pdf_reports",
    "excel_reports",
    "json_reports",
]

# Managed directories that are NEVER cleaned
_PRESERVED_DIRECTORIES: list[str] = [
    "uploads",
    "thumbnails",
]


# ---------------------------------------------------------------------------
# Core logic (separated from CLI for testability)
# ---------------------------------------------------------------------------


def clean_outputs(
    file_manager: FileManager,
    *,
    include_logs: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Remove generated artifacts from cleanable output directories.

    Args:
        file_manager: Initialized ``FileManager`` instance.
        include_logs: If ``True``, also clean the logs directory.
        dry_run: If ``True``, simulate without deleting any files.

    Returns:
        Dictionary summarizing the cleanup:
        - ``directories_scanned``: Number of directories checked.
        - ``files_deleted``: Total number of files removed.
        - ``bytes_freed``: Total bytes freed.
        - ``errors``: List of error messages (if any).
        - ``details``: Per-directory breakdown.

    Raises:
        FileOperationError: If a critical file operation fails.
    """
    result: dict[str, Any] = {
        "directories_scanned": 0,
        "files_deleted": 0,
        "bytes_freed": 0,
        "errors": [],
        "details": [],
    }

    dirs_to_clean = list(_CLEANABLE_DIRECTORIES)
    if include_logs:
        dirs_to_clean.append("logs")

    for dir_name in dirs_to_clean:
        try:
            dir_info = _clean_single_directory(
                file_manager, dir_name, dry_run=dry_run
            )
            result["directories_scanned"] += 1
            result["files_deleted"] += dir_info["files_deleted"]
            result["bytes_freed"] += dir_info["bytes_freed"]
            result["details"].append(dir_info)

            if dir_info["files_deleted"] > 0:
                logger.info(
                    "Cleaned %s: %d files, %s freed",
                    dir_name,
                    dir_info["files_deleted"],
                    _format_size(dir_info["bytes_freed"]),
                )
            else:
                logger.debug("Directory '%s' is already clean.", dir_name)

        except (FileOperationError, NotADirectoryError, FileNotFoundError) as exc:
            logger.warning("Error cleaning directory '%s': %s", dir_name, exc)
            result["errors"].append(str(exc))

    return result


def _clean_single_directory(
    file_manager: FileManager,
    dir_name: str,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Remove all files from a single cleanable directory.

    Args:
        file_manager: Initialized ``FileManager`` instance.
        dir_name: Managed directory name to clean.
        dry_run: If ``True``, simulate without deleting.

    Returns:
        Dictionary with ``dir_name``, ``files_deleted``, ``bytes_freed``,
        and ``path``.

    Raises:
        FileOperationError: If the directory cannot be resolved or cleaned.
        NotADirectoryError: If the path is not a directory.
    """
    # Resolve path
    if dir_name == "logs":
        dir_path = Path(settings.LOG_DIR)
    else:
        try:
            dir_path = Path(
                getattr(settings, file_manager._MANAGED_DIRECTORIES[dir_name])
            )
        except KeyError:
            raise FileOperationError(
                f"Unknown managed directory: '{dir_name}'."
            )

    if not dir_path.exists():
        return {
            "dir_name": dir_name,
            "path": str(dir_path),
            "files_deleted": 0,
            "bytes_freed": 0,
        }

    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    # Collect files
    files_to_delete: list[Path] = sorted(
        p for p in dir_path.rglob("*") if p.is_file()
    )

    if not files_to_delete:
        return {
            "dir_name": dir_name,
            "path": str(dir_path),
            "files_deleted": 0,
            "bytes_freed": 0,
        }

    if dry_run:
        total_size = sum(p.stat().st_size for p in files_to_delete)
        logger.info(
            "[DRY-RUN] Would delete %d file(s) from '%s' (%s)",
            len(files_to_delete),
            dir_name,
            _format_size(total_size),
        )
        return {
            "dir_name": dir_name,
            "path": str(dir_path),
            "files_deleted": len(files_to_delete),
            "bytes_freed": total_size,
        }

    # Delete files
    deleted = 0
    bytes_freed = 0
    for file_path in files_to_delete:
        try:
            size = file_path.stat().st_size
            file_path.unlink()
            deleted += 1
            bytes_freed += size
            logger.debug("Deleted: %s (%s)", file_path, _format_size(size))
        except OSError as exc:
            logger.warning("Failed to delete %s: %s", file_path, exc)

    # Remove empty subdirectories (bottom-up)
    for subdir in sorted(dir_path.rglob("*"), key=lambda p: len(str(p)), reverse=True):
        if subdir.is_dir() and not any(subdir.iterdir()):
            try:
                subdir.rmdir()
                logger.debug("Removed empty directory: %s", subdir)
            except OSError:
                pass

    return {
        "dir_name": dir_name,
        "path": str(dir_path),
        "files_deleted": deleted,
        "bytes_freed": bytes_freed,
    }


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
    """Print a human-readable summary of the cleanup operation.

    Args:
        result: Result dictionary from :func:`clean_outputs`.
    """
    separator = "=" * 60
    print(f"\n{separator}")
    print(f"  {settings.PROJECT_NAME} — Clean Outputs Summary")
    print(f"{separator}")
    print(f"  Directories Scanned : {result['directories_scanned']}")
    print(f"  Files Deleted       : {result['files_deleted']:,}")
    print(f"  Space Freed         : {_format_size(result['bytes_freed'])}")
    if result["errors"]:
        print(f"  Errors              : {len(result['errors'])}")
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
        prog="clean_outputs",
        description="Remove generated artifacts from VisionOps AI output directories.",
        epilog="Example: python -m backend.scripts.clean_outputs --confirm",
    )
    parser.add_argument(
        "--confirm",
        "-y",
        action="store_true",
        help="Skip confirmation prompt and proceed with cleanup.",
    )
    parser.add_argument(
        "--include-logs",
        action="store_true",
        help="Also clean the logs directory.",
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
        help="Simulate cleanup without deleting any files.",
    )
    return parser


def _prompt_confirmation(result: dict[str, Any]) -> bool:
    """Prompt the user to confirm the cleanup operation.

    Args:
        result: Preview of what will be deleted.

    Returns:
        ``True`` if the user confirms, ``False`` otherwise.
    """
    print(f"\nWARNING: This will delete {result['files_deleted']:,} file(s) "
          f"({_format_size(result['bytes_freed'])}) from the following directories:")
    for detail in result["details"]:
        if detail["files_deleted"] > 0:
            print(f"  - {detail['dir_name']}: {detail['files_deleted']} file(s)")
    print()

    response = input("Proceed with cleanup? [y/N]: ").strip().lower()
    return response in ("y", "yes")


def main() -> int:
    """Execute the output cleanup workflow.

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

    logger.info("=== VisionOps AI — Clean Outputs ===")
    logger.info("Script started: clean_outputs.py")

    if args.dry_run:
        logger.info("DRY-RUN mode enabled — no files will be deleted.")

    try:
        file_manager = FileManager()
    except FileOperationError as exc:
        logger.error("Failed to initialise FileManager: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return _EXIT_FAILURE

    # Compute what would be cleaned (preview)
    try:
        preview = clean_outputs(
            file_manager,
            include_logs=args.include_logs,
            dry_run=True,
        )
    except FileOperationError as exc:
        logger.error("Failed to compute cleanup preview: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return _EXIT_FAILURE

    if preview["files_deleted"] == 0:
        print("No files to clean — all output directories are already empty.")
        logger.info("All cleanable directories are already empty.")
        return _EXIT_SUCCESS

    # Confirmation
    if not args.confirm and not args.dry_run:
        if not _prompt_confirmation(preview):
            print("Cleanup cancelled.")
            logger.info("Cleanup cancelled by user.")
            return _EXIT_SUCCESS

    # Execute cleanup
    try:
        result = clean_outputs(
            file_manager,
            include_logs=args.include_logs,
            dry_run=args.dry_run,
        )
    except FileOperationError as exc:
        logger.error("Cleanup failed: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return _EXIT_FAILURE

    _print_result(result)

    if result["errors"]:
        logger.warning("=== Cleanup completed with %d error(s) ===", len(result["errors"]))
        return _EXIT_FAILURE

    logger.info("=== Cleanup completed successfully ===")
    return _EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
