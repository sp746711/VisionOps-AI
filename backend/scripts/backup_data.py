#!/usr/bin/env python3
"""VisionOps AI — Backup Data Script.

Creates a timestamped backup of all project data using the
``BackupManager``.  Supports optional custom labels, backup integrity
verification, and a summary of backup size.

Usage:
    python -m backend.scripts.backup_data
    python -m backend.scripts.backup_data --label before_upgrade
    python -m backend.scripts.backup_data --verbose
    python -m backend.scripts.backup_data --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.exceptions import StorageError
from backend.storage import BackupManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EXIT_SUCCESS: int = 0
_EXIT_FAILURE: int = 1


# ---------------------------------------------------------------------------
# Core logic (separated from CLI for testability)
# ---------------------------------------------------------------------------


def create_backup(
    backup_manager: BackupManager,
    *,
    label: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Create a timestamped backup of project data.

    Args:
        backup_manager: Initialized ``BackupManager`` instance.
        label: Optional human-readable label for the backup.
        dry_run: If ``True``, simulate without creating a backup.

    Returns:
        Dictionary with backup metadata:
        - ``backup_path``: Absolute path to the created backup directory.
        - ``label``: The label used (if any).
        - ``file_count``: Number of files in the backup.
        - ``size_bytes``: Total size of the backup in bytes.
        - ``existing_backups``: Total number of backups now available.

    Raises:
        StorageError: If the backup creation fails.
    """
    if dry_run:
        label_str = f" (label='{label}')" if label else ""
        logger.info("[DRY-RUN] Would create backup%s", label_str)
        return {
            "backup_path": "",
            "label": label or "",
            "file_count": 0,
            "size_bytes": 0,
            "existing_backups": len(backup_manager.list_backups()),
        }

    logger.info("Creating backup%s…", f" (label='{label}')" if label else "")
    backup_path = backup_manager.create_backup(label=label)

    # Collect metadata
    bp = Path(backup_path)
    file_count = sum(1 for _ in bp.rglob("*") if _.is_file())
    size_bytes = sum(p.stat().st_size for p in bp.rglob("*") if p.is_file())
    existing_backups = len(backup_manager.list_backups())

    result: dict[str, Any] = {
        "backup_path": str(bp.resolve()),
        "label": label or "",
        "file_count": file_count,
        "size_bytes": size_bytes,
        "existing_backups": existing_backups,
    }

    logger.info(
        "Backup created: %s (%d files, %s bytes)",
        result["backup_path"],
        file_count,
        _format_size(size_bytes),
    )

    return result


def verify_backup(backup_path: str | Path) -> dict[str, Any]:
    """Verify the integrity of a backup directory.

    Checks that the backup path exists, is a directory, contains at least
    one file, and has a recognisable backup name.

    Args:
        backup_path: Path to the backup directory to verify.

    Returns:
        Dictionary with verification results:
        - ``path``: Resolved backup path.
        - ``exists``: Whether the path exists.
        - ``is_directory``: Whether it is a directory.
        - ``file_count``: Number of files in the backup.
        - ``size_bytes``: Total size in bytes.
        - ``valid``: Overall validity flag.
        - ``issues``: List of issues found (empty if valid).
    """
    bp = Path(backup_path).resolve()
    issues: list[str] = []
    file_count = 0
    size_bytes = 0

    if not bp.exists():
        issues.append("Path does not exist.")
    elif not bp.is_dir():
        issues.append("Path is not a directory.")
    else:
        if "backup_" not in bp.name:
            issues.append("Directory name does not contain 'backup_'.")

        for p in bp.rglob("*"):
            if p.is_file():
                file_count += 1
                size_bytes += p.stat().st_size

        if file_count == 0:
            issues.append("Backup directory is empty (no files).")

    return {
        "path": str(bp),
        "exists": bp.exists(),
        "is_directory": bp.is_dir() if bp.exists() else False,
        "file_count": file_count,
        "size_bytes": size_bytes,
        "valid": len(issues) == 0,
        "issues": issues,
    }


def _print_backup_result(result: dict[str, Any]) -> None:
    """Print a human-readable summary of the backup operation.

    Args:
        result: Result dictionary from :func:`create_backup`.
    """
    separator = "=" * 60
    print(f"\n{separator}")
    print(f"  {settings.PROJECT_NAME} — Backup Summary")
    print(f"{separator}")
    if result["backup_path"]:
        print(f"  Backup Path  : {result['backup_path']}")
    if result["label"]:
        print(f"  Label        : {result['label']}")
    print(f"  File Count   : {result['file_count']:,}")
    print(f"  Size         : {_format_size(result['size_bytes'])}")
    print(f"  Backups Now  : {result['existing_backups']}")
    print(f"{separator}\n")


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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI.

    Returns:
        Configured ``ArgumentParser`` instance.
    """
    parser = argparse.ArgumentParser(
        prog="backup_data",
        description="Create a timestamped backup of VisionOps AI project data.",
        epilog="Example: python -m backend.scripts.backup_data --label pre_upgrade",
    )
    parser.add_argument(
        "--label",
        "-l",
        type=str,
        default=None,
        help="Optional human-readable label for the backup (e.g. 'before_upgrade').",
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
        help="Simulate backup creation without making any changes.",
    )
    return parser


def main() -> int:
    """Execute the backup workflow.

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

    logger.info("=== VisionOps AI — Backup Data ===")
    logger.info("Script started: backup_data.py")

    if args.dry_run:
        logger.info("DRY-RUN mode enabled — no changes will be made.")
    if args.label:
        logger.info("Backup label: '%s'", args.label)

    try:
        backup_manager = BackupManager()
        logger.info("Backup directory: %s", backup_manager.backup_dir)
    except StorageError as exc:
        logger.error("Failed to initialise BackupManager: %s", exc)
        print(f"ERROR: {exc}", file=sys.stderr)
        return _EXIT_FAILURE

    try:
        result = create_backup(
            backup_manager,
            label=args.label,
            dry_run=args.dry_run,
        )
    except StorageError as exc:
        logger.error("Backup creation failed: %s", exc)
        print(f"ERROR: Backup failed: {exc}", file=sys.stderr)
        return _EXIT_FAILURE

    # Verify the backup if it was created
    if result["backup_path"]:
        logger.info("Verifying backup integrity…")
        verification = verify_backup(result["backup_path"])
        if verification["valid"]:
            logger.info("Backup integrity check passed.")
        else:
            for issue in verification["issues"]:
                logger.warning("Backup verification issue: %s", issue)
            logger.warning("Backup may be incomplete.")

    _print_backup_result(result)

    logger.info("=== Backup completed successfully ===")
    return _EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
