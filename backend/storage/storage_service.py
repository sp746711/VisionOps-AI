"""VisionOps AI — Unified storage service facade.

Provides a single entry point to all storage-layer managers:

* :class:`CSVManager`       — CSV data stores
* :class:`JSONManager`      — JSON data stores
* :class:`FileManager`      — File-system operations
* :class:`ArchiveManager`   — Archival of data directories
* :class:`BackupManager`    — Backup / restore

Usage::

    from backend.storage import StorageService

    storage = StorageService()
    storage.initialize()

    videos = storage.csv_manager.read_videos()
    summary = storage.json_manager.read_summary()
    storage.file_manager.ensure_directories()
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.exceptions import StorageError
from backend.storage.archive_manager import ArchiveManager
from backend.storage.backup_manager import BackupManager
from backend.storage.csv_manager import CSVManager
from backend.storage.file_manager import FileManager
from backend.storage.json_manager import JSONManager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# StorageService
# ---------------------------------------------------------------------------


class StorageService:
    """Unified facade over all VisionOps AI storage managers.

    Encapsulates :class:`CSVManager`, :class:`JSONManager`,
    :class:`FileManager`, :class:`ArchiveManager`, and
    :class:`BackupManager` behind a single interface.  Call
    :meth:`initialize` once during application startup to ensure all
    managed directories exist.

    The facade also exposes convenience methods that delegate to the
    appropriate sub-manager for common cross-cutting operations.

    Raises:
        StorageError: Wraps errors from any underlying manager.
    """

    def __init__(
        self,
        csv_delimiter: str = ",",
        json_encoding: str = "utf-8",
        json_indent: int | None = 2,
        archive_format: str = "zip",
        backup_dir: str | Path | None = None,
    ) -> None:
        """Initialise all storage sub-managers.

        Args:
            csv_delimiter: Field delimiter for CSV files (default: ``,``).
            json_encoding: File encoding for JSON files (default:
                ``utf-8``).
            json_indent: Pretty-print indent for JSON files (default:
                ``2``).  Pass ``None`` for compact output.
            archive_format: Archive format — one of ``zip``, ``tar``,
                ``gztar``, ``bztar``, ``xztar`` (default: ``zip``).
            backup_dir: Root directory for backups.  If ``None``,
                defaults to ``settings.ARCHIVE_FOLDER / "backups"``.
        """
        self.csv_manager = CSVManager(delimiter=csv_delimiter)
        self.json_manager = JSONManager(
            encoding=json_encoding,
            indent=json_indent,
        )
        self.file_manager = FileManager()
        self.archive_manager = ArchiveManager(
            archive_format=archive_format,
        )
        self.backup_manager = BackupManager(
            backup_dir=backup_dir,
        )

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> dict[str, Path]:
        """Perform one-time initialization of the storage layer.

        Ensures all managed directories (uploads, outputs, reports,
        archive, backup) exist.

        Call this method during application startup.

        Returns:
            Dictionary mapping directory name to resolved ``Path``
            from :meth:`FileManager.ensure_directories`.
        """
        logger.info("Initialising VisionOps AI storage layer…")
        dirs = self.file_manager.ensure_directories()
        self.archive_manager.archive_base_dir.mkdir(parents=True, exist_ok=True)
        self.backup_manager.backup_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Storage layer initialised — %d managed directories",
            len(dirs),
        )
        return dirs

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """Return a summary of the storage layer status.

        Returns:
            Dictionary with keys:
            * ``initialized`` — ``True`` if all managed directories exist.
            * ``csv_stores`` — List of CSV store metadata.
            * ``json_stores`` — List of JSON store metadata.
            * ``managed_directories`` — List of managed directory metadata.
            * ``backup_info`` — Backup manager summary.
        """
        # Check if all managed directories exist
        dirs = self.file_manager.list_managed_directories()
        all_exist = all(p.is_dir() for p in dirs.values())

        return {
            "initialized": all_exist,
            "csv_stores": [
                self.csv_manager.store_info(name)
                for name in self.csv_manager.store_names()
            ],
            "json_stores": [
                self.json_manager.store_info(name)
                for name in self.json_manager.store_names()
            ],
            "managed_directories": [
                self.file_manager.directory_info(name)
                for name in self.file_manager.managed_directory_names()
            ],
            "backup_info": self.backup_manager.backup_info(),
        }

    # ------------------------------------------------------------------
    # Cross-cutting operations
    # ------------------------------------------------------------------

    def create_snapshot(self, label: str | None = None) -> Path:
        """Create a full data snapshot (alias for backup).

        Args:
            label: Optional label for the snapshot.

        Returns:
            Absolute ``Path`` of the backup directory.
        """
        return self.backup_manager.create_backup(label=label)

    def archive_and_clean(
        self,
        data_dir: str,
        archive_name: str | None = None,
    ) -> Path:
        """Archive a data directory and return the archive path.

        This is a convenience that combines :meth:`ArchiveManager.archive_directory`
        with a simple workflow step.

        Args:
            data_dir: One of ``raw``, ``processed``, ``analytics``.
            archive_name: Optional archive stem.

        Returns:
            Absolute ``Path`` of the created archive.
        """
        return self.archive_manager.archive_directory(
            data_dir,
            archive_name=archive_name,
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cleanup_temp_files(self, pattern: str = "*.tmp") -> int:
        """Remove temporary files from managed directories.

        Scans all managed directories for files matching *pattern* and
        deletes them.

        Args:
            pattern: Glob pattern to match (default: ``"*.tmp"``).

        Returns:
            Number of files deleted.
        """
        deleted = 0
        for name in self.file_manager.managed_directory_names():
            try:
                dir_path = Path(
                    getattr(settings, self.file_manager._MANAGED_DIRECTORIES[name])
                )
                if not dir_path.is_dir():
                    continue
                for tmp_file in dir_path.glob(pattern):
                    try:
                        tmp_file.unlink()
                        deleted += 1
                        logger.debug("Deleted temp file: %s", tmp_file)
                    except OSError as exc:
                        logger.warning(
                            "Failed to delete temp file %s: %s",
                            tmp_file,
                            exc,
                        )
            except Exception as exc:
                logger.warning(
                    "Error cleaning directory '%s': %s", name, exc
                )

        if deleted:
            logger.info("Cleaned %d temp file(s) (pattern='%s')", deleted, pattern)
        return deleted

    # ------------------------------------------------------------------
    # Convenience — CSV passthrough
    # ------------------------------------------------------------------

    def read_csv_store(self, store_name: str) -> list[dict[str, str]]:
        """Read a CSV data store by name.

        Args:
            store_name: One of ``videos``, ``detections``, ``events``,
                ``alerts``, ``kpis``, ``analytics``.

        Returns:
            List of row dictionaries.
        """
        return self.csv_manager.read_store(store_name)

    def write_csv_store(
        self,
        store_name: str,
        data: list[dict[str, Any]],
        fieldnames: list[str] | None = None,
    ) -> Path:
        """Write (overwrite) a CSV data store by name.

        Args:
            store_name: Named CSV store.
            data: List of dictionaries to persist.
            fieldnames: Column order (optional).

        Returns:
            Resolved ``Path`` of the written file.
        """
        return self.csv_manager.write_store(store_name, data, fieldnames=fieldnames)

    def append_csv_store(
        self,
        store_name: str,
        rows: list[dict[str, Any]],
    ) -> Path:
        """Append rows to a CSV data store by name.

        Args:
            store_name: Named CSV store.
            rows: List of dictionaries to append.

        Returns:
            Resolved ``Path`` of the appended file.
        """
        return self.csv_manager.append_store(store_name, rows)

    # ------------------------------------------------------------------
    # Convenience — JSON passthrough
    # ------------------------------------------------------------------

    def read_json_store(self, store_name: str) -> Any:
        """Read a JSON data store by name.

        Args:
            store_name: Named JSON store (e.g. ``summary``).

        Returns:
            Deserialized data.
        """
        return self.json_manager.read_store(store_name)

    def write_json_store(
        self,
        store_name: str,
        data: Any,
        sort_keys: bool = False,
    ) -> Path:
        """Write (overwrite) a JSON data store by name.

        Args:
            store_name: Named JSON store.
            data: Data to serialize.
            sort_keys: Sort dictionary keys in output.

        Returns:
            Resolved ``Path`` of the written file.
        """
        return self.json_manager.write_store(
            store_name, data, sort_keys=sort_keys
        )

    # ------------------------------------------------------------------
    # Convenience — File passthrough
    # ------------------------------------------------------------------

    def file_exists(self, path: str | Path) -> bool:
        """Check whether a file exists (path-validated).

        Args:
            path: Path to check.

        Returns:
            ``True`` if the path is a regular file.
        """
        return self.file_manager.exists(path)

    def delete_file(self, path: str | Path, missing_ok: bool = True) -> None:
        """Delete a file (path-validated).

        Args:
            path: Path to the file.
            missing_ok: Silently return if missing (default: ``True``).
        """
        self.file_manager.delete(path, missing_ok=missing_ok)

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"StorageService(csv={type(self.csv_manager).__name__}, "
            f"json={type(self.json_manager).__name__}, "
            f"file={type(self.file_manager).__name__}, "
            f"archive={type(self.archive_manager).__name__}, "
            f"backup={type(self.backup_manager).__name__})"
        )
