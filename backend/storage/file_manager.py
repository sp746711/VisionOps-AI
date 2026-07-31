"""VisionOps AI — High-level file operation manager.

Provides a config-aware interface for common file-system operations
within the VisionOps AI project's managed directories (uploads, outputs,
reports).  Built on top of ``backend.utils.file_utils``.

Usage::

    from backend.storage.file_manager import FileManager

    mgr = FileManager()
    mgr.ensure_directories()
    path = mgr.save_uploaded_file(b"content", "video.mp4")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.exceptions import FileOperationError
from backend.utils.file_utils import (
    copy_file,
    create_directory,
    delete_file,
    directory_size,
    file_exists,
    file_hash,
    file_size,
    list_files,
    move_file,
    rename_file,
    ensure_directory,
    safe_path,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# FileManager
# ---------------------------------------------------------------------------


class FileManager:
    """High-level manager for file operations inside VisionOps AI's
    managed directories.

    Provides convenience methods for saving uploaded files, managing
    output directories (annotated videos, extracted frames, detection
    images, previews), and report directories (PDF, Excel, JSON).

    All paths are resolved through the global ``settings`` object and
    validated against directory traversal attacks.

    Raises:
        FileOperationError: Wraps any underlying file-system error.
    """

    # ------------------------------------------------------------------
    # Directory names as they appear in settings
    # ------------------------------------------------------------------

    _MANAGED_DIRECTORIES: dict[str, str] = {
        "uploads": "UPLOAD_FOLDER",
        "thumbnails": "THUMBNAIL_FOLDER",
        "annotated_videos": "ANNOTATED_VIDEOS_DIR",
        "extracted_frames": "EXTRACTED_FRAMES_DIR",
        "detection_images": "DETECTION_IMAGES_DIR",
        "previews": "PREVIEW_IMAGES_DIR",
        "pdf_reports": "PDF_REPORTS_DIR",
        "excel_reports": "EXCEL_REPORTS_DIR",
        "json_reports": "JSON_REPORTS_DIR",
    }

    def __init__(self, base_dir: str | Path | None = None) -> None:
        """Initialise the file manager.

        Args:
            base_dir: Base directory for path-safety checks.  If
                ``None``, defaults to the project root obtained from
                ``settings.base_dir``.
        """
        self._base_dir = Path(base_dir) if base_dir else settings.base_dir

    # ------------------------------------------------------------------
    # Directory resolution
    # ------------------------------------------------------------------

    def _resolve_managed_dir(self, name: str) -> Path:
        """Resolve the absolute path of a managed directory.

        Args:
            name: Key in ``_MANAGED_DIRECTORIES``.

        Returns:
            Resolved absolute ``Path``.

        Raises:
            FileOperationError: If *name* is unknown.
        """
        attr = self._MANAGED_DIRECTORIES.get(name)
        if attr is None:
            raise FileOperationError(
                f"Unknown managed directory '{name}'. "
                f"Available: {list(self._MANAGED_DIRECTORIES)}"
            )
        return Path(getattr(settings, attr))

    def managed_directory_names(self) -> list[str]:
        """Return the list of recognised managed directory names.

        Returns:
            Sorted list of name strings.
        """
        return sorted(self._MANAGED_DIRECTORIES)

    def ensure_directories(self) -> dict[str, Path]:
        """Ensure all managed directories exist, creating them as needed.

        Returns:
            Dictionary mapping directory name to resolved ``Path``.
        """
        result: dict[str, Path] = {}
        for name in self._MANAGED_DIRECTORIES:
            path = self._resolve_managed_dir(name)
            ensure_directory(path)
            result[name] = path
            logger.debug("Ensured directory: %s -> %s", name, path)
        return result

    # ------------------------------------------------------------------
    # Upload helpers
    # ------------------------------------------------------------------

    def save_uploaded_file(
        self,
        content: bytes,
        filename: str,
        subdir: str | None = None,
    ) -> Path:
        """Save uploaded file bytes to the uploads directory.

        Args:
            content: Raw file bytes.
            filename: Desired filename (may include a relative sub-path).
            subdir: Optional subdirectory within the uploads folder
                (e.g. ``"videos"``).

        Returns:
            Absolute ``Path`` of the saved file.

        Raises:
            FileOperationError: If the write fails or a path traversal is
                detected.
        """
        upload_dir = self._resolve_managed_dir("uploads")
        target_dir = upload_dir / subdir if subdir else upload_dir
        ensure_directory(target_dir)
        target_path = safe_path(target_dir / filename, base_dir=upload_dir)

        try:
            target_path.write_bytes(content)
            logger.info(
                "Saved uploaded file (%d bytes): %s", len(content), target_path
            )
            return target_path
        except OSError as exc:
            raise FileOperationError(
                f"Failed to save uploaded file {filename}: {exc}",
                path=str(target_path),
            ) from exc

    def save_thumbnail(
        self,
        content: bytes,
        filename: str,
    ) -> Path:
        """Save a thumbnail image to the thumbnails directory.

        Args:
            content: Raw image bytes.
            filename: Thumbnail filename.

        Returns:
            Absolute ``Path`` of the saved thumbnail.
        """
        thumb_dir = self._resolve_managed_dir("thumbnails")
        ensure_directory(thumb_dir)
        target_path = safe_path(thumb_dir / filename, base_dir=thumb_dir)

        try:
            target_path.write_bytes(content)
            logger.info("Saved thumbnail (%d bytes): %s", len(content), target_path)
            return target_path
        except OSError as exc:
            raise FileOperationError(
                f"Failed to save thumbnail {filename}: {exc}",
                path=str(target_path),
            ) from exc

    # ------------------------------------------------------------------
    # Output file helpers
    # ------------------------------------------------------------------

    def save_output_file(
        self,
        content: bytes,
        filename: str,
        output_type: str,
    ) -> Path:
        """Save a file to one of the managed output directories.

        Args:
            content: Raw file bytes.
            filename: Desired filename.
            output_type: One of ``annotated_videos``, ``extracted_frames``,
                ``detection_images``, ``previews``.

        Returns:
            Absolute ``Path`` of the saved file.

        Raises:
            FileOperationError: If *output_type* is unknown or the write
                fails.
        """
        out_dir = self._resolve_managed_dir(output_type)
        ensure_directory(out_dir)
        target_path = safe_path(out_dir / filename, base_dir=out_dir)

        try:
            target_path.write_bytes(content)
            logger.info(
                "Saved %s output (%d bytes): %s",
                output_type,
                len(content),
                target_path,
            )
            return target_path
        except OSError as exc:
            raise FileOperationError(
                f"Failed to save {output_type} output {filename}: {exc}",
                path=str(target_path),
            ) from exc

    def save_report_file(
        self,
        content: bytes,
        filename: str,
        report_type: str,
    ) -> Path:
        """Save a generated report file to the appropriate directory.

        Args:
            content: Raw file bytes.
            filename: Report filename (including extension).
            report_type: One of ``pdf_reports``, ``excel_reports``,
                ``json_reports``.

        Returns:
            Absolute ``Path`` of the saved file.

        Raises:
            FileOperationError: If *report_type* is unknown or the write
                fails.
        """
        report_dir = self._resolve_managed_dir(report_type)
        ensure_directory(report_dir)
        target_path = safe_path(report_dir / filename, base_dir=report_dir)

        try:
            target_path.write_bytes(content)
            logger.info(
                "Saved %s report (%d bytes): %s",
                report_type,
                len(content),
                target_path,
            )
            return target_path
        except OSError as exc:
            raise FileOperationError(
                f"Failed to save {report_type} report {filename}: {exc}",
                path=str(target_path),
            ) from exc

    # ------------------------------------------------------------------
    # Generic file operations
    # ------------------------------------------------------------------

    def copy(
        self,
        src: str | Path,
        dst: str | Path,
        overwrite: bool = False,
    ) -> Path:
        """Copy a file, validating paths against the base directory.

        Args:
            src: Source path.
            dst: Destination path (or directory).
            overwrite: Overwrite existing destination (default: ``False``).

        Returns:
            Resolved ``Path`` of the destination file.

        Raises:
            FileOperationError: On failure.
        """
        safe_src = safe_path(src, base_dir=self._base_dir)
        safe_dst = safe_path(dst, base_dir=self._base_dir)
        try:
            return copy_file(safe_src, safe_dst, overwrite=overwrite)
        except (FileNotFoundError, FileExistsError, OSError) as exc:
            raise FileOperationError(
                f"Copy failed: {exc}", path=str(safe_src)
            ) from exc

    def move(
        self,
        src: str | Path,
        dst: str | Path,
        overwrite: bool = False,
    ) -> Path:
        """Move a file, validating paths against the base directory.

        Args:
            src: Source path.
            dst: Destination path (or directory).
            overwrite: Overwrite existing destination (default: ``False``).

        Returns:
            Resolved ``Path`` of the destination file.

        Raises:
            FileOperationError: On failure.
        """
        safe_src = safe_path(src, base_dir=self._base_dir)
        safe_dst = safe_path(dst, base_dir=self._base_dir)
        try:
            return move_file(safe_src, safe_dst, overwrite=overwrite)
        except (FileNotFoundError, FileExistsError, OSError) as exc:
            raise FileOperationError(
                f"Move failed: {exc}", path=str(safe_src)
            ) from exc

    def rename(
        self,
        path: str | Path,
        new_name: str,
        overwrite: bool = False,
    ) -> Path:
        """Rename a file, validating against the base directory.

        Args:
            path: Path to the file.
            new_name: New filename (can include extension).
            overwrite: Overwrite existing target (default: ``False``).

        Returns:
            Resolved ``Path`` of the renamed file.

        Raises:
            FileOperationError: On failure.
        """
        safe_src = safe_path(path, base_dir=self._base_dir)
        try:
            return rename_file(safe_src, new_name, overwrite=overwrite)
        except (FileNotFoundError, FileExistsError, OSError) as exc:
            raise FileOperationError(
                f"Rename failed: {exc}", path=str(safe_src)
            ) from exc

    def delete(
        self,
        path: str | Path,
        missing_ok: bool = True,
    ) -> None:
        """Delete a file, validating against the base directory.

        Args:
            path: Path to the file.
            missing_ok: Silently return if file is missing
                (default: ``True``).

        Raises:
            FileOperationError: On failure.
        """
        safe_target = safe_path(path, base_dir=self._base_dir)
        try:
            delete_file(safe_target, missing_ok=missing_ok)
        except (FileNotFoundError, IsADirectoryError, PermissionError) as exc:
            raise FileOperationError(
                f"Delete failed: {exc}", path=str(safe_target)
            ) from exc

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def exists(self, path: str | Path) -> bool:
        """Check whether a file exists (validated against base dir).

        Args:
            path: Path to check.

        Returns:
            ``True`` if the path is a regular file.
        """
        safe_target = safe_path(path, base_dir=self._base_dir)
        return file_exists(safe_target)

    def size(
        self,
        path: str | Path,
        unit: str = "B",
    ) -> int | float:
        """Get the size of a file.

        Args:
            path: Path to the file.
            unit: Unit — ``"B"``, ``"KB"``, ``"MB"``, ``"GB"``
                (default: ``"B"``).

        Returns:
            File size in the requested unit.

        Raises:
            FileOperationError: On failure.
        """
        safe_target = safe_path(path, base_dir=self._base_dir)
        try:
            return file_size(safe_target, unit=unit)
        except (FileNotFoundError, IsADirectoryError) as exc:
            raise FileOperationError(
                f"Size check failed: {exc}", path=str(safe_target)
            ) from exc

    def hash(
        self,
        path: str | Path,
        algorithm: str = "sha256",
    ) -> str:
        """Compute the hash of a file's contents.

        Args:
            path: Path to the file.
            algorithm: Hash algorithm (default: ``"sha256"``).

        Returns:
            Hex digest string.

        Raises:
            FileOperationError: On failure.
        """
        safe_target = safe_path(path, base_dir=self._base_dir)
        try:
            return file_hash(safe_target, algorithm=algorithm)
        except (FileNotFoundError, ValueError, IsADirectoryError) as exc:
            raise FileOperationError(
                f"Hash failed: {exc}", path=str(safe_target)
            ) from exc

    def list_files(
        self,
        directory: str | Path,
        pattern: str | None = None,
        recursive: bool = False,
    ) -> list[Path]:
        """List files in a directory, validated against the base dir.

        Args:
            directory: Directory to scan.
            pattern: Optional glob pattern (e.g. ``"*.csv"``).
            recursive: Recurse into subdirectories (default: ``False``).

        Returns:
            Sorted list of file ``Path`` objects.

        Raises:
            FileOperationError: On failure.
        """
        safe_dir = safe_path(directory, base_dir=self._base_dir)
        try:
            return list_files(safe_dir, pattern=pattern, recursive=recursive)
        except (FileNotFoundError, NotADirectoryError) as exc:
            raise FileOperationError(
                f"List files failed: {exc}", path=str(safe_dir)
            ) from exc

    def directory_size(
        self,
        directory: str | Path,
    ) -> int:
        """Calculate total size (in bytes) of all files in a directory.

        Args:
            directory: Path to the directory.

        Returns:
            Total size in bytes.

        Raises:
            FileOperationError: On failure.
        """
        safe_dir = safe_path(directory, base_dir=self._base_dir)
        try:
            return directory_size(safe_dir)
        except (FileNotFoundError, NotADirectoryError) as exc:
            raise FileOperationError(
                f"Directory size check failed: {exc}", path=str(safe_dir)
            ) from exc

    # ------------------------------------------------------------------
    # Info
    # ------------------------------------------------------------------

    def directory_info(self, name: str) -> dict[str, Any]:
        """Return metadata about a managed directory.

        Args:
            name: Managed directory name.

        Returns:
            Dictionary with keys ``name``, ``path``, ``exists``,
            ``file_count``, ``size_bytes``.
        """
        path = self._resolve_managed_dir(name)
        exists = path.is_dir()
        if exists:
            files = [p for p in path.rglob("*") if p.is_file()]
            total_size = sum(p.stat().st_size for p in files)
            file_count = len(files)
        else:
            file_count = 0
            total_size = 0

        return {
            "name": name,
            "path": str(path),
            "exists": exists,
            "file_count": file_count,
            "size_bytes": total_size,
        }

    def list_managed_directories(self) -> dict[str, Path]:
        """Return a mapping of managed directory names to their paths.

        Returns:
            Dictionary ``{name: resolved_path}``.
        """
        return {
            name: self._resolve_managed_dir(name)
            for name in self._MANAGED_DIRECTORIES
        }

