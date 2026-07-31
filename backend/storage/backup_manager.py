"""VisionOps AI — Backup manager for data directory backup & restore.

Provides timestamped backup creation and restore functionality for the
data directories (raw, processed, analytics) as well as individual CSV
and JSON data stores.

Usage::

    from backend.storage.backup_manager import BackupManager

    mgr = BackupManager()
    backup_path = mgr.create_backup()
    mgr.restore_backup(backup_path)
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.exceptions import StorageError
from backend.utils.file_utils import copy_file, ensure_directory, list_files

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backup directories
# ---------------------------------------------------------------------------

_DATA_DIRECTORIES: dict[str, str] = {
    "raw": "RAW_FOLDER",
    "processed": "PROCESSED_FOLDER",
    "analytics": "ANALYTICS_FOLDER",
}

_CSV_STORE_KEYS: tuple[str, ...] = (
    "VIDEOS_CSV",
    "DETECTIONS_CSV",
    "EVENTS_CSV",
    "ALERTS_CSV",
    "KPIS_CSV",
    "ANALYTICS_CSV",
)

_JSON_STORE_KEYS: tuple[str, ...] = (
    "SUMMARY_JSON",
)

# ---------------------------------------------------------------------------
# BackupManager
# ---------------------------------------------------------------------------


class BackupManager:
    """Manager for creating and restoring backups of VisionOps AI data.

    Backups are stored as timestamped directories inside a dedicated
    backup location.  Each backup snapshot includes:

    * Data directories (raw, processed, analytics).
    * CSV data-store files (videos, detections, events, alerts, KPIs,
      analytics).
    * JSON data-store files (summary).

    Raises:
        StorageError: Wraps any underlying file-system or backup error.
    """

    def __init__(
        self,
        backup_dir: str | Path | None = None,
    ) -> None:
        """Initialise the backup manager.

        Args:
            backup_dir: Root directory for storing backups.  If
                ``None``, defaults to ``settings.ARCHIVE_FOLDER / "backups"``.
        """
        self._backup_dir = (
            Path(backup_dir)
            if backup_dir
            else Path(settings.ARCHIVE_FOLDER) / "backups"
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def backup_dir(self) -> Path:
        """Return the root backup directory."""
        return self._backup_dir

    # ------------------------------------------------------------------
    # Backup creation
    # ------------------------------------------------------------------

    def _resolve_data_dir(self, name: str) -> Path:
        """Resolve the absolute path of a named data directory.

        Args:
            name: One of ``raw``, ``processed``, ``analytics``.

        Returns:
            Resolved absolute ``Path``.

        Raises:
            StorageError: If *name* is unknown.
        """
        attr = _DATA_DIRECTORIES.get(name)
        if attr is None:
            raise StorageError(
                f"Unknown data directory '{name}'. "
                f"Available: {list(_DATA_DIRECTORIES)}"
            )
        return Path(getattr(settings, attr))

    def create_backup(
        self,
        label: str | None = None,
    ) -> Path:
        """Create a full timestamped backup of all data.

        Copies data directories and data-store files into a timestamped
        subdirectory under ``backup_dir``.

        Args:
            label: Optional human-readable label appended to the backup
                directory name (e.g. ``"before_upgrade"``).

        Returns:
            Absolute ``Path`` of the backup directory.

        Raises:
            StorageError: If any copy operation fails.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{label}" if label else ""
        backup_name = f"backup_{timestamp}{suffix}"
        target_dir = self._backup_dir / backup_name

        ensure_directory(target_dir)
        errors: list[str] = []

        try:
            # 1. Copy data directories
            for dir_name in _DATA_DIRECTORIES:
                source = self._resolve_data_dir(dir_name)
                if source.is_dir():
                    dest = target_dir / dir_name
                    try:
                        shutil.copytree(
                            str(source),
                            str(dest),
                            dirs_exist_ok=True,
                        )
                        logger.info(
                            "Backed up directory '%s' -> %s",
                            dir_name,
                            dest,
                        )
                    except OSError as exc:
                        errors.append(
                            f"Failed to backup directory '{dir_name}': {exc}"
                        )
                else:
                    logger.warning(
                        "Skipping backup of '%s': directory does not exist (%s)",
                        dir_name,
                        source,
                    )

            # 2. Copy CSV data-store files
            for key in _CSV_STORE_KEYS:
                source = Path(getattr(settings, key))
                if source.is_file():
                    dest = target_dir / "csv" / source.name
                    ensure_directory(dest.parent)
                    try:
                        copy_file(source, dest, overwrite=True)
                        logger.info("Backed up CSV: %s", source.name)
                    except OSError as exc:
                        errors.append(
                            f"Failed to backup CSV '{source.name}': {exc}"
                        )
                else:
                    logger.debug(
                        "Skipping CSV backup: %s not found", source
                    )

            # 3. Copy JSON data-store files
            for key in _JSON_STORE_KEYS:
                source = Path(getattr(settings, key))
                if source.is_file():
                    dest = target_dir / "json" / source.name
                    ensure_directory(dest.parent)
                    try:
                        copy_file(source, dest, overwrite=True)
                        logger.info("Backed up JSON: %s", source.name)
                    except OSError as exc:
                        errors.append(
                            f"Failed to backup JSON '{source.name}': {exc}"
                        )
                else:
                    logger.debug(
                        "Skipping JSON backup: %s not found", source
                    )

        except OSError as exc:
            raise StorageError(
                f"Backup creation failed: {exc}"
            ) from exc

        if errors:
            logger.warning(
                "Backup completed with %d error(s): %s",
                len(errors),
                "; ".join(errors),
            )

        logger.info(
            "Backup created successfully: %s (%d files)",
            target_dir,
            self._count_files(target_dir),
        )
        return target_dir.resolve()

    def _count_files(self, directory: Path) -> int:
        """Count regular files in a directory (non-recursive helper)."""
        return sum(1 for _ in directory.rglob("*") if _.is_file())

    # ------------------------------------------------------------------
    # Restore
    # ------------------------------------------------------------------

    def restore_backup(
        self,
        backup_path: str | Path,
        include_dirs: bool = True,
        include_csv: bool = True,
        include_json: bool = True,
    ) -> dict[str, Any]:
        """Restore data from a previously created backup.

        Args:
            backup_path: Path to the backup directory (created by
                :meth:`create_backup`).
            include_dirs: If ``True`` (default), restore data directories.
            include_csv: If ``True`` (default), restore CSV store files.
            include_json: If ``True`` (default), restore JSON store files.

        Returns:
            Dictionary summarizing the restore operation with keys:
            ``backup_path``, ``restored_dirs``, ``restored_csvs``,
            ``restored_jsons``, ``errors``.

        Raises:
            StorageError: If the backup directory does not exist.
        """
        backup = Path(backup_path).resolve()

        if not backup.is_dir():
            raise StorageError(
                f"Backup directory not found: {backup}"
            )

        result: dict[str, Any] = {
            "backup_path": str(backup),
            "restored_dirs": [],
            "restored_csvs": [],
            "restored_jsons": [],
            "errors": [],
        }

        # 1. Restore data directories
        if include_dirs:
            for dir_name in _DATA_DIRECTORIES:
                source = backup / dir_name
                if source.is_dir():
                    target = self._resolve_data_dir(dir_name)
                    ensure_directory(target)
                    try:
                        shutil.copytree(
                            str(source),
                            str(target),
                            dirs_exist_ok=True,
                        )
                        result["restored_dirs"].append(dir_name)
                        logger.info(
                            "Restored directory '%s' from %s",
                            dir_name,
                            source,
                        )
                    except OSError as exc:
                        msg = (
                            f"Failed to restore directory "
                            f"'{dir_name}': {exc}"
                        )
                        result["errors"].append(msg)
                        logger.error(msg)

        # 2. Restore CSV files
        if include_csv:
            csv_source = backup / "csv"
            if csv_source.is_dir():
                for csv_file in csv_source.glob("*.csv"):
                    # Find the matching settings key by filename
                    target = self._find_csv_target(csv_file.name)
                    if target:
                        try:
                            copy_file(csv_file, target, overwrite=True)
                            result["restored_csvs"].append(csv_file.name)
                            logger.info(
                                "Restored CSV: %s", csv_file.name
                            )
                        except OSError as exc:
                            msg = (
                                f"Failed to restore CSV "
                                f"'{csv_file.name}': {exc}"
                            )
                            result["errors"].append(msg)
                            logger.error(msg)
                    else:
                        logger.warning(
                            "Unknown CSV file in backup: %s",
                            csv_file.name,
                        )

        # 3. Restore JSON files
        if include_json:
            json_source = backup / "json"
            if json_source.is_dir():
                for json_file in json_source.glob("*.json"):
                    target = self._find_json_target(json_file.name)
                    if target:
                        try:
                            copy_file(json_file, target, overwrite=True)
                            result["restored_jsons"].append(json_file.name)
                            logger.info(
                                "Restored JSON: %s", json_file.name
                            )
                        except OSError as exc:
                            msg = (
                                f"Failed to restore JSON "
                                f"'{json_file.name}': {exc}"
                            )
                            result["errors"].append(msg)
                            logger.error(msg)
                    else:
                        logger.warning(
                            "Unknown JSON file in backup: %s",
                            json_file.name,
                        )

        logger.info(
            "Restore completed from %s: %d dirs, %d CSVs, %d JSONs "
            "(%d error(s))",
            backup,
            len(result["restored_dirs"]),
            len(result["restored_csvs"]),
            len(result["restored_jsons"]),
            len(result["errors"]),
        )

        return result

    def _find_csv_target(self, filename: str) -> Path | None:
        """Map a CSV filename from backup to its settings path.

        Args:
            filename: CSV filename (e.g. ``videos.csv``).

        Returns:
            Resolved ``Path`` from settings, or ``None`` if unknown.
        """
        for key in _CSV_STORE_KEYS:
            path = Path(getattr(settings, key))
            if path.name == filename:
                return path
        return None

    def _find_json_target(self, filename: str) -> Path | None:
        """Map a JSON filename from backup to its settings path.

        Args:
            filename: JSON filename (e.g. ``summary.json``).

        Returns:
            Resolved ``Path`` from settings, or ``None`` if unknown.
        """
        for key in _JSON_STORE_KEYS:
            path = Path(getattr(settings, key))
            if path.name == filename:
                return path
        return None

    # ------------------------------------------------------------------
    # Listing & info
    # ------------------------------------------------------------------

    def list_backups(self) -> list[dict[str, Any]]:
        """List all available backups in the backup directory.

        Returns:
            Sorted list (newest first) of dictionaries with keys:
            ``path``, ``name``, ``created`` (ISO timestamp), ``size_bytes``,
            ``file_count``.
        """
        if not self._backup_dir.is_dir():
            return []

        backups: list[dict[str, Any]] = []
        for entry in sorted(self._backup_dir.iterdir(), reverse=True):
            if entry.is_dir() and entry.name.startswith("backup_"):
                total_size = sum(
                    p.stat().st_size for p in entry.rglob("*") if p.is_file()
                )
                file_count = sum(
                    1 for p in entry.rglob("*") if p.is_file()
                )
                # Extract timestamp from directory name
                created_str = entry.name.replace("backup_", "")[:15]
                try:
                    created = datetime.strptime(created_str, "%Y%m%d_%H%M%S")
                    created_iso = created.isoformat()
                except ValueError:
                    created_iso = created_str

                backups.append({
                    "path": str(entry.resolve()),
                    "name": entry.name,
                    "created": created_iso,
                    "size_bytes": total_size,
                    "file_count": file_count,
                })

        return backups

    def backup_info(self) -> dict[str, Any]:
        """Return metadata about the backup manager and its storage.

        Returns:
            Dictionary with keys ``backup_dir``, ``total_backups``,
            ``total_size_bytes``.
        """
        backups = self.list_backups()
        total_size = sum(b["size_bytes"] for b in backups)
        return {
            "backup_dir": str(self._backup_dir.resolve()),
            "total_backups": len(backups),
            "total_size_bytes": total_size,
        }

    def delete_backup(self, backup_path: str | Path) -> None:
        """Delete a backup directory.

        Args:
            backup_path: Path to the backup directory to delete.

        Raises:
            StorageError: If the path is not a valid backup directory or
                deletion fails.
        """
        target = Path(backup_path).resolve()

        if not target.exists():
            raise StorageError(f"Backup not found: {target}")
        if not target.is_dir():
            raise StorageError(
                f"Not a directory: {target}. "
                f"Use FileManager.delete() for files."
            )
        if "backup_" not in target.name:
            raise StorageError(
                f"Not a recognised backup directory: {target.name}"
            )

        try:
            shutil.rmtree(str(target))
            logger.info("Deleted backup: %s", target)
        except OSError as exc:
            raise StorageError(
                f"Failed to delete backup '{target}': {exc}"
            ) from exc

