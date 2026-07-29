"""VisionOps AI — Validation Utilities.

Reusable generic validation helpers for file paths, directories, UUIDs,
emails, numeric ranges, required values, filenames, extensions, URLs,
IP addresses, and ports. Shared across the entire backend.

Usage:
    from backend.utils.validation import validate_uuid, validate_email, ...
"""

from __future__ import annotations

import ipaddress
import logging
import re
import uuid
from pathlib import Path
from typing import Any, Sequence

logger = logging.getLogger("visionops.utils.validation")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EMAIL_PATTERN: re.Pattern[str] = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)
_URL_PATTERN: re.Pattern[str] = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}\.?|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d{1,5})?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)
_ALLOWED_FILENAME_CHARS: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9._-]+$")


# ---------------------------------------------------------------------------
# File Path
# ---------------------------------------------------------------------------


def validate_file_path(path: str | Path, must_exist: bool = True) -> Path:
    """Validate a file path.

    Args:
        path: The path to validate.
        must_exist: If ``True`` (default), the file must exist on disk.

    Returns:
        The resolved ``Path`` if valid.

    Raises:
        FileNotFoundError: If *must_exist* is True and file not found.
        IsADirectoryError: If path exists but is a directory.
        ValueError: If the path is empty or invalid.

    Example:
        >>> validate_file_path("/etc/hosts")
    """
    if not isinstance(path, (str, Path)):
        raise TypeError(f"Expected str or Path, got {type(path).__name__}")

    file_path = Path(path)
    if not file_path.name:
        raise ValueError(f"Path is empty: {path!r}")

    if must_exist and not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.exists() and file_path.is_dir():
        raise IsADirectoryError(f"Path is a directory, not a file: {file_path}")

    return file_path.resolve()


# ---------------------------------------------------------------------------
# Directory
# ---------------------------------------------------------------------------


def validate_directory(path: str | Path, must_exist: bool = True) -> Path:
    """Validate a directory path.

    Args:
        path: The directory path to validate.
        must_exist: If ``True`` (default), directory must exist.

    Returns:
        The resolved ``Path`` if valid.

    Raises:
        FileNotFoundError: If *must_exist* is True and dir not found.
        NotADirectoryError: If path exists but is not a directory.
        ValueError: If path is empty.

    Example:
        >>> validate_directory("/var/log")
    """
    dir_path = Path(path)
    if not dir_path.name:
        raise ValueError(f"Path is empty: {path!r}")

    if must_exist and not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {dir_path}")

    if dir_path.exists() and not dir_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {dir_path}")

    return dir_path.resolve()


# ---------------------------------------------------------------------------
# UUID
# ---------------------------------------------------------------------------


def validate_uuid(value: str, version: int = 4) -> bool:
    """Validate that a string is a valid UUID of the specified version.

    Args:
        value: UUID string to validate.
        version: UUID version (1, 3, 4, or 5; default: 4).

    Returns:
        ``True`` if the string is a valid UUID of the given version.

    Raises:
        ValueError: If *version* is not 1, 3, 4, or 5.

    Example:
        >>> validate_uuid("550e8400-e29b-41d4-a716-446655440000")
        True
    """
    if version not in {1, 3, 4, 5}:
        raise ValueError(
            f"Unsupported UUID version: {version}. Must be 1, 3, 4, or 5."
        )

    if not isinstance(value, str) or not value.strip():
        return False

    try:
        val = uuid.UUID(value.strip())
        return val.version == version
    except (ValueError, AttributeError):
        return False


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------


def validate_email(value: str) -> bool:
    """Validate an email address using a regex pattern.

    Validates format only — does not verify domain existence or MX records.

    Args:
        value: Email string to validate.

    Returns:
        ``True`` if the email has a valid format.

    Example:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("not-an-email")
        False
    """
    if not isinstance(value, str) or not value.strip():
        return False

    return bool(_EMAIL_PATTERN.match(value.strip()))


# ---------------------------------------------------------------------------
# Numeric Range
# ---------------------------------------------------------------------------


def validate_numeric_range(
    value: float | int,
    min_val: float | int | None = None,
    max_val: float | int | None = None,
    inclusive: bool = True,
) -> bool:
    """Validate that a numeric value falls within a specified range.

    Args:
        value: The numeric value to check.
        min_val: Minimum allowed (or None).
        max_val: Maximum allowed (or None).
        inclusive: If True (default), boundaries are inclusive.

    Returns:
        ``True`` if the value is within range.

    Raises:
        TypeError: If *value* is not numeric.

    Example:
        >>> validate_numeric_range(5, 0, 10)
        True
    """
    if not isinstance(value, (int, float)):
        raise TypeError(f"Expected numeric type, got {type(value).__name__}")

    if inclusive:
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
    else:
        if min_val is not None and value <= min_val:
            return False
        if max_val is not None and value >= max_val:
            return False

    return True


# ---------------------------------------------------------------------------
# Required Values
# ---------------------------------------------------------------------------


def validate_required_values(
    data: dict[str, Any],
    required_keys: Sequence[str],
) -> bool:
    """Validate that a dict contains all required keys with non-None values.

    Args:
        data: Dictionary to validate.
        required_keys: Keys that must be present and non-None.

    Returns:
        ``True`` if all required keys are present.

    Raises:
        ValueError: Listing missing keys.

    Example:
        >>> validate_required_values({"a": 1}, ["a", "b"])
        ValueError: Missing required keys: b
    """
    missing: list[str] = []
    for key in required_keys:
        if key not in data or data[key] is None:
            missing.append(key)

    if missing:
        raise ValueError(f"Missing required keys: {', '.join(missing)}")

    return True


# ---------------------------------------------------------------------------
# Filename
# ---------------------------------------------------------------------------


def validate_filename(
    value: str,
    max_length: int = 255,
    allowed_chars: re.Pattern[str] | None = None,
) -> bool:
    """Validate a filename string (without path).

    Args:
        value: Filename to validate.
        max_length: Max length (default: 255).
        allowed_chars: Regex pattern of allowed chars.
            Default: ``[a-zA-Z0-9._-]``.

    Returns:
        ``True`` if filename is valid.

    Raises:
        ValueError: If filename is empty, too long, or has invalid chars.

    Example:
        >>> validate_filename("report_2025.csv")
        True
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Filename cannot be empty")

    name = value.strip()
    if len(name) > max_length:
        raise ValueError(
            f"Filename exceeds max length of {max_length}: {len(name)}"
        )

    if "/" in name or "\\" in name:
        raise ValueError(f"Filename contains path separator: {name!r}")

    reserved = {
        "CON", "PRN", "AUX", "NUL",
        "COM1", "COM2", "COM3", "COM4",
        "COM5", "COM6", "COM7", "COM8", "COM9",
        "LPT1", "LPT2", "LPT3", "LPT4",
        "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    }
    stem = Path(name).stem.upper()
    if stem in reserved:
        raise ValueError(f"Filename uses reserved name: {name!r}")

    pattern = allowed_chars or _ALLOWED_FILENAME_CHARS
    if not pattern.match(name):
        raise ValueError(f"Filename contains disallowed characters: {name!r}")

    return True


# ---------------------------------------------------------------------------
# Extension
# ---------------------------------------------------------------------------


def validate_extension(
    filename: str,
    allowed_extensions: Sequence[str],
    case_sensitive: bool = False,
) -> bool:
    """Validate that a filename has an allowed extension.

    Args:
        filename: Filename to check (e.g. ``"data.csv"``).
        allowed_extensions: Allowed extensions (e.g. ``[".csv", ".json"]``).
        case_sensitive: If False (default), case-insensitive.

    Returns:
        ``True`` if extension is allowed.

    Raises:
        ValueError: If no extension or extension not allowed.

    Example:
        >>> validate_extension("data.csv", [".csv", ".json"])
        True
    """
    file_path = Path(filename)
    ext = file_path.suffix
    if not ext:
        raise ValueError(f"Filename has no extension: {filename!r}")

    norm_ext = ext.lower() if not case_sensitive else ext
    norm_allowed = [
        (e.lower() if not case_sensitive else e)
        for e in allowed_extensions
    ]
    norm_allowed = [
        e if e.startswith(".") else f".{e}" for e in norm_allowed
    ]

    if norm_ext not in norm_allowed:
        raise ValueError(
            f"Extension '{ext}' not allowed for {filename!r}. "
            f"Allowed: {allowed_extensions}"
        )

    return True


# ---------------------------------------------------------------------------
# URL
# ---------------------------------------------------------------------------


def validate_url(value: str) -> bool:
    """Validate a URL (http or https).

    Args:
        value: URL string to validate.

    Returns:
        ``True`` if a valid HTTP(S) URL.

    Example:
        >>> validate_url("https://example.com/api")
        True
    """
    if not isinstance(value, str) or not value.strip():
        return False
    return bool(_URL_PATTERN.match(value.strip()))


# ---------------------------------------------------------------------------
# IP
# ---------------------------------------------------------------------------


def validate_ip(value: str) -> bool:
    """Validate an IP address (IPv4 or IPv6).

    Args:
        value: IP address string to validate.

    Returns:
        ``True`` if a valid IPv4 or IPv6 address.

    Example:
        >>> validate_ip("192.168.1.1")
        True
        >>> validate_ip("::1")
        True
    """
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        ipaddress.ip_address(value.strip())
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Port
# ---------------------------------------------------------------------------


def validate_port(value: int) -> bool:
    """Validate a TCP/UDP port number (1-65535).

    Args:
        value: Port number to validate.

    Returns:
        ``True`` if a valid port number.

    Raises:
        TypeError: If *value* is not an integer.

    Example:
        >>> validate_port(8080)
        True
        >>> validate_port(0)
        False
    """
    if not isinstance(value, int):
        raise TypeError(f"Expected int, got {type(value).__name__}")
    return 1 <= value <= 65535
