"""VisionOps AI — CSV Utilities.

Reusable low-level CSV helpers for reading, writing, validating, and
manipulating CSV data. These are generic primitives used across the
entire backend (storage, services, analytics, workers).

Usage:
    from backend.utils.csv_utils import read_csv, write_csv
"""

from __future__ import annotations

import csv
import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Sequence

logger = logging.getLogger("visionops.utils.csv_utils")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ENCODING: str = "utf-8"
DEFAULT_DELIMITER: str = ","
COMMON_DELIMITERS: tuple[str, ...] = (",", "\t", ";", "|", ":")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def read_csv(
    path: str | Path,
    delimiter: str | None = None,
    encoding: str = DEFAULT_ENCODING,
    skip_empty: bool = True,
) -> list[dict[str, str]]:
    """Read a CSV file and return contents as a list of dictionaries.

    Args:
        path: Path to the CSV file.
        delimiter: Field delimiter. If ``None``, auto-detected.
        encoding: File encoding (default: ``utf-8``).
        skip_empty: If ``True``, skip rows where all fields are empty.

    Returns:
        List of dicts keyed by header names.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is empty or has no headers, or CSV parsing
            fails.

    Example:
        >>> rows = read_csv("data.csv", delimiter=",")
    """
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    if filepath.stat().st_size == 0:
        raise ValueError(f"CSV file is empty: {filepath}")

    delim = delimiter if delimiter is not None else detect_delimiter(filepath, encoding)

    try:
        with filepath.open("r", encoding=encoding, newline="") as fh:
            reader = csv.DictReader(fh, delimiter=delim)
            if reader.fieldnames is None:
                raise ValueError(f"CSV file has no headers: {filepath}")

            rows: list[dict[str, str]] = []
            for row in reader:
                if skip_empty and all(v.strip() == "" for v in row.values()):
                    continue
                rows.append(row)

            logger.info("Read %d rows from %s (delimiter='%s')", len(rows), filepath, delim)
            return rows

    except csv.Error as exc:
        raise ValueError(f"CSV parsing error in {filepath}: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ValueError(f"Encoding error reading {filepath} with {encoding}: {exc}") from exc


def write_csv(
    path: str | Path,
    data: Sequence[dict[str, Any]],
    fieldnames: Sequence[str] | None = None,
    delimiter: str = DEFAULT_DELIMITER,
    encoding: str = DEFAULT_ENCODING,
    mode: str = "w",
) -> Path:
    """Write a list of dictionaries to a CSV file (atomic write).

    Uses a temporary file and rename to prevent partial writes.

    Args:
        path: Destination file path.
        data: List of dictionaries to write. May be empty if *fieldnames* is
            provided.
        fieldnames: Column order. If ``None``, inferred from keys of first dict.
        delimiter: Field delimiter (default: ``,``).
        encoding: File encoding (default: ``utf-8``).
        mode: ``"w"`` to overwrite, ``"a"`` to append.

    Returns:
        Resolved ``Path`` of the written file.

    Raises:
        ValueError: If both *data* and *fieldnames* are empty.
        OSError: If the write fails.

    Example:
        >>> write_csv("out.csv", [{"a": 1, "b": 2}])
    """
    filepath = Path(path)
    headers = _resolve_fieldnames(data, fieldnames)

    if not headers:
        raise ValueError("Cannot write CSV: no data and no fieldnames provided")

    if mode == "a" and filepath.exists():
        return _append_csv(filepath, data, headers, delimiter, encoding)

    filepath.parent.mkdir(parents=True, exist_ok=True)

    tmp_path: Path | None = None
    try:
        fd, tmp_path_str = tempfile.mkstemp(
            suffix=filepath.suffix or ".csv",
            prefix="csv_",
            dir=filepath.parent,
        )
        tmp_path = Path(tmp_path_str)

        with open(fd, "w", encoding=encoding, newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(headers), delimiter=delimiter)
            writer.writeheader()
            writer.writerows(data)

        shutil.move(str(tmp_path), str(filepath))
        logger.info("Wrote %d rows to %s", len(data), filepath)
        return filepath

    except (OSError, csv.Error) as exc:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()
        raise OSError(f"Failed to write CSV to {filepath}: {exc}") from exc


def _resolve_fieldnames(
    data: Sequence[dict[str, Any]],
    fieldnames: Sequence[str] | None,
) -> list[str]:
    """Resolve the list of fieldnames from data or explicit argument."""
    if fieldnames is not None:
        return list(fieldnames)
    if data:
        return list(data[0].keys())
    return []


def _append_csv(
    filepath: Path,
    data: Sequence[dict[str, Any]],
    fieldnames: list[str],
    delimiter: str,
    encoding: str,
) -> Path:
    """Append rows to an existing CSV file."""
    try:
        with filepath.open("a", encoding=encoding, newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, delimiter=delimiter)
            writer.writerows(data)
        logger.info("Appended %d rows to %s", len(data), filepath)
        return filepath
    except (OSError, csv.Error) as exc:
        raise OSError(f"Failed to append to {filepath}: {exc}") from exc


def append_rows(
    path: str | Path,
    rows: Sequence[dict[str, Any]],
    delimiter: str = DEFAULT_DELIMITER,
    encoding: str = DEFAULT_ENCODING,
) -> Path:
    """Append rows to an existing CSV file.

    Args:
        path: Path to the CSV file.
        rows: List of dictionaries to append.
        delimiter: Field delimiter (default: ``,``).
        encoding: File encoding (default: ``utf-8``).

    Returns:
        Resolved ``Path`` of the file that was appended to.

    Raises:
        ValueError: If the file does not exist (use :func:`write_csv` to create).
        OSError: If the append fails.
    """
    filepath = Path(path)
    if not filepath.exists():
        raise ValueError(f"Cannot append — file not found: {filepath}")

    return write_csv(filepath, rows, delimiter=delimiter, encoding=encoding, mode="a")


def update_rows(
    path: str | Path,
    match_fn: Callable[[dict[str, str]], bool],
    update_fn: Callable[[dict[str, str]], dict[str, str]],
    delimiter: str = DEFAULT_DELIMITER,
    encoding: str = DEFAULT_ENCODING,
) -> int:
    """Update rows in a CSV file that satisfy a predicate.

    Reads the full file, applies *update_fn* to matching rows, and
    rewrites the file atomically.

    Args:
        path: Path to the CSV file.
        match_fn: Predicate — receives a row dict, returns ``True`` if the
            row should be updated.
        update_fn: Mutator — receives a row dict, returns the updated row.
        delimiter: Field delimiter (default: ``,``).
        encoding: File encoding (default: ``utf-8``).

    Returns:
        Number of rows updated.

    Raises:
        ValueError: If the file cannot be read or written.
    """
    filepath = Path(path)
    rows = read_csv(filepath, delimiter=delimiter, encoding=encoding)

    updated = 0
    for i, row in enumerate(rows):
        if match_fn(row):
            rows[i] = update_fn(row)
            updated += 1

    if updated > 0:
        write_csv(filepath, rows, delimiter=delimiter, encoding=encoding)

    logger.info("Updated %d row(s) in %s", updated, filepath)
    return updated


def validate_csv(
    path: str | Path,
    expected_headers: Sequence[str] | None = None,
    delimiter: str | None = None,
    encoding: str = DEFAULT_ENCODING,
) -> bool:
    """Validate that a CSV file is well-formed and optionally has expected headers.

    Args:
        path: Path to the CSV file.
        expected_headers: If provided, all headers must be present.
        delimiter: Field delimiter. ``None`` triggers auto-detection.
        encoding: File encoding (default: ``utf-8``).

    Returns:
        ``True`` if valid.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If validation fails (empty file, missing headers, parse error).

    Example:
        >>> validate_csv("data.csv", expected_headers=["id", "name"])
    """
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    if filepath.stat().st_size == 0:
        raise ValueError(f"CSV file is empty: {filepath}")

    delim = delimiter if delimiter is not None else detect_delimiter(filepath, encoding)

    try:
        with filepath.open("r", encoding=encoding, newline="") as fh:
            reader = csv.DictReader(fh, delimiter=delim)
            headers = reader.fieldnames

            if headers is None:
                raise ValueError(f"CSV file has no header row: {filepath}")
            if not headers:
                raise ValueError(f"CSV file has empty headers: {filepath}")

            if expected_headers is not None:
                missing = set(expected_headers) - set(headers)
                if missing:
                    raise ValueError(
                        f"Missing expected headers in {filepath}: {sorted(missing)}"
                    )

            # Read all rows to detect parse errors
            row_count = 0
            for _ in reader:
                row_count += 1

        logger.info(
            "CSV validation passed: %s (%d rows, %d columns)",
            filepath,
            row_count,
            len(headers),
        )
        return True

    except csv.Error as exc:
        raise ValueError(f"CSV parsing error in {filepath}: {exc}") from exc


def check_headers(
    path: str | Path,
    expected_headers: Sequence[str],
    delimiter: str | None = None,
    encoding: str = DEFAULT_ENCODING,
) -> bool:
    """Check that a CSV file contains all required headers.

    Args:
        path: Path to the CSV file.
        expected_headers: Headers that must be present.
        delimiter: Field delimiter. ``None`` triggers auto-detection.
        encoding: File encoding (default: ``utf-8``).

    Returns:
        ``True`` if all expected headers are present.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file has no headers.
    """
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"CSV file not found: {filepath}")

    delim = delimiter if delimiter is not None else detect_delimiter(filepath, encoding)

    try:
        with filepath.open("r", encoding=encoding, newline="") as fh:
            reader = csv.DictReader(fh, delimiter=delim)
            actual = set(reader.fieldnames) if reader.fieldnames else set()
            if not actual:
                raise ValueError(f"CSV file has no headers: {filepath}")

            expected = set(expected_headers)
            return expected.issubset(actual)

    except csv.Error as exc:
        raise ValueError(f"Failed to check headers in {filepath}: {exc}") from exc


def detect_delimiter(
    path: str | Path,
    encoding: str = DEFAULT_ENCODING,
    sample_size: int = 4096,
) -> str:
    """Detect the delimiter of a CSV file by sampling the first bytes.

    Counts occurrences of common delimiters (`,`, ``\\t``, ``;``, ``|``,
    ``:``) and returns the one with the highest count.

    Args:
        path: Path to the CSV file.
        encoding: File encoding (default: ``utf-8``).
        sample_size: Number of bytes to sample from the file (default: 4096).

    Returns:
        The most likely delimiter character.

    Raises:
        FileNotFoundError: If the file does not exist.

    Example:
        >>> delim = detect_delimiter("data.tsv")
        >>> delim
        '\\t'
    """
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        sample = filepath.read_text(encoding=encoding)[:sample_size]
    except OSError as exc:
        raise OSError(f"Cannot read {filepath} for delimiter detection: {exc}") from exc

    if not sample.strip():
        return DEFAULT_DELIMITER

    counts = {d: sample.count(d) for d in COMMON_DELIMITERS}
    # Filter out zero-count delimiters; pick the highest
    best = max((c for c in counts.items() if c[1] > 0), key=lambda x: x[1], default=None)

    detected = best[0] if best else DEFAULT_DELIMITER
    logger.debug("Detected delimiter '%s' for %s (counts=%s)", detected, filepath, counts)
    return detected


def export_csv(
    data: Sequence[dict[str, Any]],
    output_path: str | Path,
    fieldnames: Sequence[str] | None = None,
    delimiter: str = DEFAULT_DELIMITER,
    encoding: str = DEFAULT_ENCODING,
) -> Path:
    """Export data to a CSV file (convenience wrapper around :func:`write_csv`).

    Args:
        data: List of dictionaries to export.
        output_path: Destination file path.
        fieldnames: Column order. If ``None``, inferred from first dict keys.
        delimiter: Field delimiter (default: ``,``).
        encoding: File encoding (default: ``utf-8``).

    Returns:
        Resolved ``Path`` of the written file.
    """
    return write_csv(
        output_path,
        data,
        fieldnames=fieldnames,
        delimiter=delimiter,
        encoding=encoding,
        mode="w",
    )


def backup_csv(
    path: str | Path,
    backup_dir: str | Path | None = None,
    suffix: str = ".bak",
) -> Path:
    """Create a timestamped backup of a CSV file.

    Args:
        path: Path to the source CSV file.
        backup_dir: Directory for the backup. If ``None``, uses the same
            directory as the source file.
        suffix: Backup file suffix (default: ``.bak``).

    Returns:
        ``Path`` of the backup file.

    Raises:
        FileNotFoundError: If the source file does not exist.
        OSError: If the copy operation fails.
    """
    import datetime

    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"Cannot backup — file not found: {source}")

    target_dir = Path(backup_dir) if backup_dir else source.parent
    target_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{source.stem}_{ts}{suffix}{source.suffix}"
    backup_path = target_dir / backup_name

    try:
        shutil.copy2(source, backup_path)
        logger.info("Backup created: %s -> %s", source, backup_path)
    except OSError as exc:
        raise OSError(f"Backup failed for {source}: {exc}") from exc

    return backup_path


def csv_exists(path: str | Path) -> bool:
    """Check whether a CSV file exists and is non-empty.

    Args:
        path: Path to the CSV file.

    Returns:
        ``True`` if the file exists, has a ``.csv`` extension, and is
        non-empty.
    """
    filepath = Path(path)
    return (
        filepath.exists()
        and filepath.is_file()
        and filepath.suffix.lower() == ".csv"
        and filepath.stat().st_size > 0
    )
