"""VisionOps AI — Archive manager for data directory archival.

Supports compressing and extracting data directories (raw, processed,
analytics) into timestamped archive files using ``shutil.make_archive``
and ``shutil.unpack_archive``.

Usage::

    from backend.storage.archive_manager import ArchiveManager

    mgr = ArchiveManager()
    archive_path = mgr.archive_raw_data()
    mgr.extract_archive(archive_path, "data/restored")
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.exceptions import StorageError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Supported archive formats
# ---------------------------------------------------------------------------

_SUPPORTED_FORMATS: tuple[str, ...] = ("zip", "tar", "gztar", "bztar", "xztar")

# ---------------------------------------------------------------------------
# Managed data directories
# ---------------------------------------------------------------------------

_DATA_DIRECTORIES: dict[str, str] = {
    "raw": "RAW_FOLDER",
    "processed": "PROCESSED_FOLDER",
    "analytics": "ANALYTICS_FOLDER",
}


# ---------------------------------------------------------------------------
# ArchiveManager
# ---------------------------------------------------------------------------


class ArchiveManager:
    """Manager for creating and extracting compressed archives of data
    directories within the VisionOps AI project.

    Uses ``shutil.make_archive`` and ``shutil.unpack_archive`` for
    consistent, cross-platform archival operations.

    Raises:
        StorageError: Wraps any underlying archival or file-system error.
    """

    def __init__(
        self,
        archive_format: str = "zip",
        archive_base_dir: str | Path | None = None,
    ) -> None:
        """Initialise the archive manager.

        Args:
            archive_format: Archive format — one of ``"zip"``, ``"tar"``,
                ``"gztar"``, ``"bztar"``, ``"xztar"`` (default: ``"zip"``).
            archive_base_dir: Directory where archive files are stored.
                If ``None``, defaults to ``settings.ARCHIVE_FOLDER``.

        Raises:
            StorageError: If *archive_format* is not supported.
        """
        if archive_format not in _SUPPORTED_FORMATS:
            raise StorageError(
                f"Unsupported archive format '{archive_format}'. "
                f"Supported: {_SUPPORTED_FORMATS}"
            )
        self._format = archive_format
        self._archive_base_dir = (
            Path(archive_base_dir)
            if archive_base_dir
            else Path(settings.ARCHIVE_FOLDER)
        )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def archive_formats(self) -> tuple[str, ...]:
        """Return the supported archive format identifiers."""
        return _SUPPORTED_FORMATS

    @property
    def archive_base_dir(self) -> Path:
        """Return the base directory where archives are stored."""
        return self._archive_base_dir

    @property
    def data_directories(self) -> dict[str, str]:
        """Return the mapping of data directory names to their paths."""
        return _DATA_DIRECTORIES

    # ------------------------------------------------------------------
    # Archive creation
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

    def archive_directory(
        self,
        dir_name: str,
        archive_name: str | None = None,
    ) -> Path:
        """Compress a data directory into an archive file.

        The archive is placed inside ``archive_base_dir`` with a
        timestamped filename if *archive_name* is not provided.

        Args:
            dir_name: One of ``raw``, ``processed``, ``analytics``.
            archive_name: Explicit archive stem (without extension).  If
                ``None``, auto-generated as
                ``{dir_name}_{YYYYMMDD_HHMMSS}``.

        Returns:
            Absolute ``Path`` of the created archive file.

        Raises:
            StorageError: If the source directory does not exist or
                archival fails.
        """
        source_dir = self._resolve_data_dir(dir_name)

        if not source_dir.is_dir():
            raise StorageError(
                f"Cannot archive — directory does not exist: {source_dir}"
            )

        self._archive_base_dir.mkdir(parents=True, exist_ok=True)

        if archive_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{dir_name}_{timestamp}"

        # shutil.make_archive strips the dir path — use base path as root
        archive_path_str = str(
            self._archive_base_dir / archive_name
        )

        try:
            result_path = shutil.make_archive(
                archive_path_str,
                self._format,
                root_dir=str(source_dir.parent),
                base_dir=str(source_dir.name),
            )
            logger.info(
                "Archived '%s' -> %s (format=%s)",
                dir_name,
                result_path,
                self._format,
            )
            return Path(result_path).resolve()
        except (OSError, ValueError) as exc:
            raise StorageError(
                f"Failed to archive directory '{dir_name}' "
                f"({source_dir}): {exc}"
            ) from exc

    def archive_raw_data(self, archive_name: str | None = None) -> Path:
        """Convenience: archive the raw data directory.

        Args:
            archive_name: Optional archive stem.

        Returns:
            Absolute ``Path`` of the created archive.
        """
        return self.archive_directory("raw", archive_name=archive_name)

    def archive_processed_data(self, archive_name: str | None = None) -> Path:
        """Convenience: archive the processed data directory.

        Args:
            archive_name: Optional archive stem.

        Returns:
            Absolute ``Path`` of the created archive.
        """
        return self.archive_directory("processed", archive_name=archive_name)

    def archive_analytics_data(self, archive_name: str | None = None) -> Path:
        """Convenience: archive the analytics data directory.

        Args:
            archive_name: Optional archive stem.

        Returns:
            Absolute ``Path`` of the created archive.
        """
        return self.archive_directory("analytics", archive_name=archive_name)

    # ------------------------------------------------------------------
    # Archive extraction
    # ------------------------------------------------------------------

    def extract_archive(
        self,
        archive_path: str | Path,
        extract_dir: str | Path | None = None,
    ) -> Path:
        """Extract an archive file to a target directory.

        Args:
            archive_path: Path to the archive file.
            extract_dir: Destination directory.  If ``None``, extracts
                into ``archive_base_dir`` with the archive's stem as
                subdirectory name.

        Returns:
            Resolved ``Path`` of the extraction directory.

        Raises:
            StorageError: If the archive does not exist or extraction
                fails.
        """
        archive = Path(archive_path)

        if not archive.is_file():
            raise StorageError(
                f"Archive file not found: {archive}"
            )

        if extract_dir is None:
            extract_dir = self._archive_base_dir / archive.stem

        target = Path(extract_dir)
        target.mkdir(parents=True, exist_ok=True)

        try:
            shutil.unpack_archive(
                str(archive),
                extract_dir=str(target),
                format=self._format,
            )
            logger.info(
                "Extracted archive '%s' -> %s", archive, target
            )
            return target.resolve()
        except (OSError, ValueError, shutil.ReadError) as exc:
            raise StorageError(
                f"Failed to extract archive '{archive}' "
                f"to '{target}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Listing & info
    # ------------------------------------------------------------------

    def list_archives(self) -> list[Path]:
        """List all archive files in the archive base directory.

        Returns:
            Sorted list of archive ``Path`` objects.
        """
        if not self._archive_base_dir.is_dir():
            return []

        archives: list[Path] = []
        for ext in _SUPPORTED_FORMATS:
            # zip -> .zip, tar -> .tar, gztar -> .tar.gz, etc.
            if ext == "gztar":
                pattern = "*.tar.gz"
            elif ext == "bztar":
                pattern = "*.tar.bz2"
            elif ext == "xztar":
                pattern = "*.tar.xz"
            else:
                pattern = f"*.{ext}"

            archives.extend(
                sorted(self._archive_base_dir.glob(pattern))
            )

        return sorted(set(archives))

    def archive_info(self, archive_path: str | Path) -> dict[str, Any]:
        """Return metadata about an archive file.

        Args:
            archive_path: Path to the archive.

        Returns:
            Dictionary with keys ``path``, ``exists``, ``size_bytes``,
            ``format``.

        Raises:
            StorageError: If the archive does not exist.
        """
        path = Path(archive_path).resolve()
        if not path.is_file():
            raise StorageError(f"Archive not found: {path}")

        # Infer format from extension
        name_lower = path.name.lower()
        fmt = "zip"
        for f in _SUPPORTED_FORMATS:
            if f == "gztar" and (name_lower.endswith(".tar.gz")):
                fmt = f
                break
            elif f == "bztar" and (name_lower.endswith(".tar.bz2")):
                fmt = f
                break
            elif f == "xztar" and (name_lower.endswith(".tar.xz")):
                fmt = f
                break
            elif f != "gztar" and f != "bztar" and f != "xztar" and name_lower.endswith(f".{f}"):
                fmt = f
                break

        return {
            "path": str(path),
            "exists": True,
            "size_bytes": path.stat().st_size,
            "format": fmt,
        }

