"""VisionOps AI — File Utilities.

Reusable low-level file system helpers for creation, deletion, copy, move,
rename, hashing, and safe path manipulation. Shared across the entire
backend.

Usage:
    from backend.utils.file_utils import create_directory, delete_file, ...
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger("visionops.utils.file_utils")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BUFFER_SIZE: int = 65_536  # 64 KB read buffer for hashing


# ---------------------------------------------------------------------------
# Directory Operations
# ---------------------------------------------------------------------------


def create_directory(
    path: str | Path,
    exist_ok: bool = True,
    parents: bool = True,
) -> Path:
    """Create a directory at the given path.

    Args:
        path: Directory path to create.
        exist_ok: If ``True`` (default), no error if directory exists.
        parents: If ``True`` (default), create parent directories as needed.

    Returns:
        The resolved absolute ``Path`` of the created directory.

    Raises:
        OSError: If creation fails (permissions, read-only filesystem, etc.).
        FileExistsError: If *path* exists as a file and *exist_ok* is False.

    Example:
        >>> create_directory("/tmp/myapp/data")
    """
    dir_path = Path(path)
    try:
        dir_path.mkdir(parents=parents, exist_ok=exist_ok)
        logger.debug("Directory created/verified: %s", dir_path)
        return dir_path.resolve()
    except FileExistsError:
        raise
    except (OSError, PermissionError) as exc:
        raise OSError(f"Failed to create directory {path}: {exc}") from exc


def ensure_directory(path: str | Path) -> Path:
    """Ensure a directory exists, creating it and parents if necessary.

    Args:
        path: Directory path to ensure.

    Returns:
        The resolved absolute ``Path`` of the directory.
    """
    return create_directory(path, exist_ok=True, parents=True)


# ---------------------------------------------------------------------------
# File Operations
# ---------------------------------------------------------------------------


def delete_file(path: str | Path, missing_ok: bool = True) -> None:
    """Delete a file safely.

    Args:
        path: Path to the file to delete.
        missing_ok: If ``True`` (default), silently return if file is
            missing.

    Raises:
        IsADirectoryError: If *path* is a directory.
        PermissionError: If deletion is not allowed.
        FileNotFoundError: If *missing_ok* is False and file not found.

    Example:
        >>> delete_file("/tmp/temp.txt")
    """
    file_path = Path(path)
    if not file_path.exists():
        if missing_ok:
            logger.debug("File not found, skipping delete: %s", file_path)
            return
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.is_dir():
        raise IsADirectoryError(
            f"Cannot delete directory with delete_file: {file_path}. "
            "Use shutil.rmtree() instead."
        )

    try:
        file_path.unlink()
        logger.info("Deleted file: %s", file_path)
    except OSError as exc:
        raise OSError(f"Failed to delete {file_path}: {exc}") from exc


def copy_file(
    src: str | Path,
    dst: str | Path,
    overwrite: bool = False,
) -> Path:
    """Copy a file from *src* to *dst*.

    Args:
        src: Source file path.
        dst: Destination file path (or directory).
        overwrite: If ``True``, overwrite existing destination
            (default: ``False``).

    Returns:
        The resolved ``Path`` of the destination file.

    Raises:
        FileNotFoundError: If source does not exist.
        FileExistsError: If *dst* exists and *overwrite* is False.
        IsADirectoryError: If *src* is a directory.

    Example:
        >>> copy_file("source.txt", "backup/source.txt", overwrite=True)
    """
    source = Path(src)
    destination = Path(dst)

    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")
    if source.is_dir():
        raise IsADirectoryError(f"Source is a directory, not a file: {source}")

    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"Destination already exists: {destination}. "
            "Set overwrite=True to overwrite."
        )

    if destination.is_dir():
        destination = destination / source.name

    try:
        shutil.copy2(source, destination)
        logger.info("Copied: %s -> %s", source, destination)
        return destination.resolve()
    except OSError as exc:
        raise OSError(f"Failed to copy {source} to {destination}: {exc}") from exc


def move_file(
    src: str | Path,
    dst: str | Path,
    overwrite: bool = False,
) -> Path:
    """Move a file from *src* to *dst*.

    Args:
        src: Source file path.
        dst: Destination file path (or directory).
        overwrite: If ``True``, overwrite existing destination
            (default: ``False``).

    Returns:
        The resolved ``Path`` of the destination file.

    Raises:
        FileNotFoundError: If source does not exist.
        FileExistsError: If *dst* exists and *overwrite* is False.
        IsADirectoryError: If *src* is a directory.

    Example:
        >>> move_file("tmp.txt", "archive/tmp.txt", overwrite=True)
    """
    source = Path(src)
    destination = Path(dst)

    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source}")
    if source.is_dir():
        raise IsADirectoryError(f"Source is a directory, not a file: {source}")

    if destination.exists() and not overwrite:
        raise FileExistsError(
            f"Destination already exists: {destination}. "
            "Set overwrite=True to overwrite."
        )

    if destination.is_dir():
        destination = destination / source.name

    try:
        shutil.move(str(source), str(destination))
        logger.info("Moved: %s -> %s", source, destination)
        return destination.resolve()
    except OSError as exc:
        raise OSError(f"Failed to move {source} to {destination}: {exc}") from exc


def rename_file(
    path: str | Path,
    new_name: str,
    overwrite: bool = False,
) -> Path:
    """Rename a file within the same directory.

    Args:
        path: Path to the file to rename.
        new_name: New filename (can include extension).
        overwrite: If ``True``, overwrite existing file with the new name
            (default: ``False``).

    Returns:
        The resolved ``Path`` of the renamed file.

    Raises:
        FileNotFoundError: If source does not exist.
        FileExistsError: If target already exists and *overwrite* is False.
        IsADirectoryError: If *path* is a directory.

    Example:
        >>> rename_file("data.csv", "data_2025.csv")
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if file_path.is_dir():
        raise IsADirectoryError(f"Path is a directory, not a file: {file_path}")

    new_path = file_path.with_name(new_name)

    if new_path.exists() and not overwrite:
        raise FileExistsError(
            f"Target already exists: {new_path}. "
            "Set overwrite=True to overwrite."
        )

    try:
        file_path.rename(new_path)
        logger.info("Renamed: %s -> %s", file_path, new_path)
        return new_path.resolve()
    except OSError as exc:
        raise OSError(f"Failed to rename {file_path} to {new_path}: {exc}") from exc


# ---------------------------------------------------------------------------
# Existence & Size
# ---------------------------------------------------------------------------


def file_exists(path: str | Path) -> bool:
    """Check whether a file exists and is a regular file (not a directory).

    Args:
        path: Path to check.

    Returns:
        ``True`` if the path exists and is a file.
    """
    return Path(path).is_file()


def file_size(
    path: str | Path,
    unit: str = "B",
) -> int | float:
    """Get the size of a file in the specified unit.

    Args:
        path: Path to the file.
        unit: Unit — ``"B"`` (bytes), ``"KB"``, ``"MB"``, ``"GB"``
            (default: ``"B"``).

    Returns:
        File size in the requested unit (int for bytes, float otherwise).

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If *path* is a directory.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if file_path.is_dir():
        raise IsADirectoryError(f"Path is a directory: {file_path}")

    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
    divisor = units.get(unit.upper(), 1)
    size = file_path.stat().st_size
    return size if divisor == 1 else round(size / divisor, 2)


def directory_size(path: str | Path) -> int:
    """Calculate the total size (in bytes) of all files in a directory.

    Args:
        path: Path to the directory.

    Returns:
        Total size in bytes.

    Raises:
        NotADirectoryError: If *path* is not a directory.
        FileNotFoundError: If *path* does not exist.
    """
    dir_path = Path(path)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {dir_path}")
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {dir_path}")

    total = 0
    for entry in dir_path.rglob("*"):
        if entry.is_file():
            total += entry.stat().st_size

    logger.debug("Directory size of %s: %d bytes", dir_path, total)
    return total


# ---------------------------------------------------------------------------
# Safe Path
# ---------------------------------------------------------------------------


def safe_path(path: str | Path, base_dir: str | Path | None = None) -> Path:
    """Resolve a path safely, preventing directory traversal attacks.

    If *base_dir* is provided, the result is guaranteed to be under that
    base directory.

    Args:
        path: The path to resolve.
        base_dir: Optional base directory that the resolved path must be
            under. If ``None``, returns the resolved path without
            containment checks.

    Returns:
        The resolved absolute ``Path``.

    Raises:
        ValueError: If the resolved path escapes *base_dir*.

    Example:
        >>> safe_path("../../etc/passwd", "/app/data")
        ValueError: Path traversal detected
    """
    resolved = Path(path).resolve()

    if base_dir is not None:
        base = Path(base_dir).resolve()
        if not base.exists():
            base.mkdir(parents=True, exist_ok=True)

        try:
            resolved.relative_to(base)
        except ValueError:
            raise ValueError(
                f"Path traversal detected: {path} resolves to {resolved}, "
                f"which is outside {base}"
            )

    return resolved


# ---------------------------------------------------------------------------
# Temporary File
# ---------------------------------------------------------------------------


@contextmanager
def temporary_file(
    suffix: str | None = ".tmp",
    prefix: str | None = "tmp_",
    dir: str | Path | None = None,
    mode: str = "w+b",
    buffering: int = -1,
    encoding: str | None = None,
    newline: str | None = None,
) -> Generator[tempfile.NamedTemporaryFile, Any, None]:
    """Context manager that creates and cleans up a temporary file.

    Args:
        suffix: Filename suffix (default: ``.tmp``).
        prefix: Filename prefix (default: ``tmp_``).
        dir: Directory for the temp file (default: system temp dir).
        mode: File open mode (default: ``w+b``).
        buffering: Buffer size (default: system default).
        encoding: File encoding (for text mode).
        newline: Newline style (for text mode).

    Yields:
        A :class:`tempfile.NamedTemporaryFile` object. The file is
        automatically deleted on context exit.

    Example:
        >>> with temporary_file(suffix=".csv") as tmp:
        ...     tmp.write(b"data")
        ...     print(tmp.name)
    """
    tmp = tempfile.NamedTemporaryFile(
        suffix=suffix,
        prefix=prefix,
        dir=dir,
        mode=mode,
        buffering=buffering,
        encoding=encoding,
        newline=newline,
        delete=True,
    )
    try:
        yield tmp
    finally:
        try:
            tmp.close()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def list_files(
    directory: str | Path,
    pattern: str | None = None,
    recursive: bool = False,
) -> list[Path]:
    """List files in a directory, optionally filtered by glob pattern.

    Args:
        directory: Directory to scan.
        pattern: Optional glob pattern (e.g. ``"*.csv"``). If ``None``,
            all files are returned.
        recursive: If ``True``, recurse into subdirectories.

    Returns:
        Sorted list of file ``Path`` objects.

    Raises:
        NotADirectoryError: If *directory* is not a directory.
        FileNotFoundError: If *directory* does not exist.

    Example:
        >>> list_files("/data", pattern="*.csv", recursive=True)
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {dir_path}")
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    glob_method = dir_path.rglob if recursive else dir_path.glob
    pattern = pattern or "*"

    files = sorted(p for p in glob_method(pattern) if p.is_file())
    return files


def list_directories(
    directory: str | Path,
    pattern: str | None = None,
) -> list[Path]:
    """List immediate subdirectories within a directory.

    Args:
        directory: Directory to scan.
        pattern: Optional glob pattern (e.g. ``"data_*"``). If ``None``,
            all directories are returned.

    Returns:
        Sorted list of directory ``Path`` objects.

    Raises:
        NotADirectoryError: If *directory* is not a directory.
        FileNotFoundError: If *directory* does not exist.
    """
    dir_path = Path(directory)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {dir_path}")
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    pattern = pattern or "*"
    dirs = sorted(p for p in dir_path.glob(pattern) if p.is_dir())
    return dirs


def is_empty_directory(path: str | Path) -> bool:
    """Check whether a directory is empty (contains no files or subdirs).

    Args:
        path: Path to the directory.

    Returns:
        ``True`` if the directory exists and is empty.

    Raises:
        NotADirectoryError: If *path* is not a directory.
    """
    dir_path = Path(path)
    if not dir_path.exists():
        logger.debug("Directory does not exist, treating as empty: %s", dir_path)
        return True
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    return not any(dir_path.iterdir())


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------


def file_hash(
    path: str | Path,
    algorithm: str = "sha256",
) -> str:
    """Compute the hash of a file's contents.

    Args:
        path: Path to the file.
        algorithm: Hash algorithm — ``"md5"``, ``"sha1"``, ``"sha256"``,
            ``"sha512"`` (default: ``"sha256"``).

    Returns:
        Hex digest string of the hash.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the algorithm is not supported.
        IsADirectoryError: If *path* is a directory.

    Example:
        >>> file_hash("data.bin")
        'e3b0c44298fc1c149afbf4c8996fb924...'
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if file_path.is_dir():
        raise IsADirectoryError(f"Path is a directory: {file_path}")

    try:
        hasher = hashlib.new(algorithm)
    except ValueError as exc:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}") from exc

    try:
        with file_path.open("rb") as f:
            while True:
                chunk = f.read(_BUFFER_SIZE)
                if not chunk:
                    break
                hasher.update(chunk)
    except OSError as exc:
        raise OSError(f"Failed to read {file_path} for hashing: {exc}") from exc

    digest = hasher.hexdigest()
    logger.debug("Hash (%s) of %s: %s", algorithm, file_path, digest)
    return digest


def directory_hash(
    path: str | Path,
    algorithm: str = "sha256",
) -> str:
    """Compute a combined hash of all files in a directory.

    Hashes each file individually (sorted by path), then hashes the
    concatenated digests to produce a single directory fingerprint.

    Args:
        path: Path to the directory.
        algorithm: Hash algorithm (default: ``"sha256"``).

    Returns:
        Hex digest string representing the directory contents.

    Raises:
        NotADirectoryError: If *path* is not a directory.
        FileNotFoundError: If *path* does not exist.

    Example:
        >>> directory_hash("/data/assets")
    """
    dir_path = Path(path)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {dir_path}")
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {dir_path}")

    try:
        hasher = hashlib.new(algorithm)
    except ValueError as exc:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}") from exc

    all_files = sorted(p for p in dir_path.rglob("*") if p.is_file())

    for file_path in all_files:
        try:
            file_digest = file_hash(file_path, algorithm=algorithm)
            rel = file_path.relative_to(dir_path)
            hasher.update(f"{rel}:{file_digest}\n".encode("utf-8"))
        except OSError as exc:
            logger.warning(
                "Skipping unreadable file during dir hash: %s (%s)",
                file_path,
                exc,
            )

    digest = hasher.hexdigest()
    logger.debug("Directory hash (%s) of %s: %s", algorithm, dir_path, digest)
    return digest
