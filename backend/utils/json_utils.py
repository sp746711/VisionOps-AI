"""VisionOps AI — JSON Utilities.

Reusable low-level JSON helpers for read, write, validate, serialize,
deserialize, merge, and deep-update operations. Shared across the
entire backend.

Usage:
    from backend.utils.json_utils import read_json, write_json
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

logger = logging.getLogger("visionops.utils.json_utils")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ENCODING: str = "utf-8"
DEFAULT_INDENT: int = 2


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------


def read_json(
    path: str | Path,
    encoding: str = DEFAULT_ENCODING,
) -> Any:
    """Read and deserialize a JSON file.

    Args:
        path: Path to the JSON file.
        encoding: File encoding (default: utf-8).

    Returns:
        Deserialized Python object.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file contains malformed JSON.
    """
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"JSON file not found: {filepath}")

    try:
        with filepath.open("r", encoding=encoding) as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in {filepath}: {exc}") from exc
    except OSError as exc:
        raise OSError(f"Failed to read {filepath}: {exc}") from exc


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------


def write_json(
    path: str | Path,
    data: Any,
    indent: int | None = DEFAULT_INDENT,
    encoding: str = DEFAULT_ENCODING,
    sort_keys: bool = False,
    cls: type[json.JSONEncoder] | None = None,
) -> Path:
    """Serialize data and write to a JSON file atomically.

    Uses a temporary file and rename to prevent partial writes.

    Args:
        path: Destination path.
        data: Data to serialize.
        indent: Pretty-print indent level (default: 2). Use None for
            compact output.
        encoding: File encoding (default: utf-8).
        sort_keys: Sort dictionary keys in output (default: False).
        cls: Optional custom JSON encoder class.

    Returns:
        The resolved Path of the written file.

    Raises:
        ValueError: If the data cannot be serialized.
        OSError: If the write fails.
    """
    filepath = Path(path)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    tmp_path: Path | None = None
    try:
        fd, tmp_path_str = tempfile.mkstemp(
            suffix=".json",
            prefix="json_",
            dir=filepath.parent,
        )
        tmp_path = Path(tmp_path_str)

        with open(fd, "w", encoding=encoding) as f:
            json.dump(
                data,
                f,
                indent=indent,
                sort_keys=sort_keys,
                cls=cls,
                ensure_ascii=False,
            )

        shutil.move(str(tmp_path), str(filepath))
        logger.debug("Wrote JSON to %s", filepath)
        return filepath

    except (TypeError, ValueError) as exc:
        raise ValueError(f"JSON serialization failed: {exc}") from exc
    except OSError as exc:
        raise OSError(f"Failed to write JSON to {filepath}: {exc}") from exc
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


# ---------------------------------------------------------------------------
# Pretty Print
# ---------------------------------------------------------------------------


def pretty_print(
    data: Any,
    indent: int = DEFAULT_INDENT,
    sort_keys: bool = False,
) -> str:
    """Return a pretty-printed JSON string representation of data.

    Args:
        data: Data to format.
        indent: Indent level (default: 2).
        sort_keys: Sort dictionary keys (default: False).

    Returns:
        Formatted JSON string.

    Raises:
        ValueError: If the data cannot be serialized.
    """
    try:
        return json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Cannot pretty-print data: {exc}") from exc


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


def validate_json(path_or_str: str | Path, encoding: str = DEFAULT_ENCODING) -> bool:
    """Validate whether a string or file path contains valid JSON.

    Args:
        path_or_str: A JSON string or a path to a JSON file.
        encoding: File encoding (default: utf-8).

    Returns:
        True if the input is valid JSON, False otherwise.
    """
    try:
        candidate = Path(str(path_or_str))
        if candidate.exists() and candidate.is_file():
            with candidate.open("r", encoding=encoding) as f:
                json.load(f)
        else:
            json.loads(str(path_or_str))
        return True
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Safe Serialization
# ---------------------------------------------------------------------------


def safe_serialize(
    obj: Any,
    default_handler: Callable[[Any], Any] | None = None,
    indent: int | None = None,
) -> str:
    """Safely serialize a Python object to a JSON string.

    Handles non-serializable types via a configurable fallback handler.
    If no handler is provided, str() is used as the fallback.

    Args:
        obj: Object to serialize.
        default_handler: Callable that converts non-serializable objects.
        indent: Optional indent level for pretty-printing.

    Returns:
        JSON string.

    Raises:
        ValueError: If serialization fails even with the fallback handler.
    """
    handler = default_handler if default_handler is not None else str

    try:
        return json.dumps(
            obj,
            default=handler,
            indent=indent,
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Safe serialization failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Safe Deserialization
# ---------------------------------------------------------------------------


def safe_deserialize(json_str: str, default: Any = None) -> Any:
    """Safely deserialize a JSON string, returning a default on failure.

    Args:
        json_str: JSON string to deserialize.
        default: Value to return if deserialization fails (default: None).

    Returns:
        Deserialized Python object, or default on failure.
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError, ValueError):
        logger.warning("safe_deserialize failed, returning default")
        return default


# ---------------------------------------------------------------------------
# Handle Malformed JSON
# ---------------------------------------------------------------------------


def _repair_json(malformed: str) -> str | None:
    """Attempt basic repair of a malformed JSON string.

    Tries common fixes: adding missing outer braces for bare key-value
    pairs, removing trailing commas, and quoting unquoted keys.

    Args:
        malformed: The malformed JSON string to repair.

    Returns:
        Repaired JSON string, or None if repair was not possible.
    """
    stripped = malformed.strip()
    if not stripped:
        return None

    if stripped.startswith('"') and ":" in stripped and not stripped.startswith("{"):
        return "{" + stripped + "}"

    repaired = re.sub(r",\s*([}\]])", r"\1", stripped)
    if repaired != stripped:
        return repaired

    repaired = re.sub(
        r'(?<!")(\b[a-zA-Z_][a-zA-Z0-9_]*\b)(?=\s*:)',
        r'"\1"',
        stripped,
    )
    if repaired != stripped:
        return repaired

    return None


def handle_malformed_json(
    path: str | Path,
    repair_attempts: bool = True,
    encoding: str = DEFAULT_ENCODING,
) -> Any:
    """Read a JSON file, attempting to repair malformed content.

    Args:
        path: Path to the JSON file.
        repair_attempts: If True, attempt basic repairs (default: True).
        encoding: File encoding (default: utf-8).

    Returns:
        Deserialized data. If repair succeeds, returns the repaired data.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file contains malformed JSON and repair fails.
    """
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        content = filepath.read_text(encoding=encoding)
    except OSError as exc:
        raise OSError(f"Cannot read file for repair: {exc}") from exc

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        if not repair_attempts:
            raise ValueError(f"Malformed JSON in {filepath}, repair not attempted")

    repaired = _repair_json(content)
    if repaired is not None:
        try:
            data = json.loads(repaired)
            logger.info("Repaired malformed JSON in %s", filepath)
            return data
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not repair malformed JSON in {filepath}")


# ---------------------------------------------------------------------------
# Merge & Deep Update
# ---------------------------------------------------------------------------


def merge_json(
    base: dict[str, Any],
    override: dict[str, Any],
    deep: bool = False,
) -> dict[str, Any]:
    """Merge two dictionaries, with override taking precedence.

    When deep is True, nested dictionaries are merged recursively.

    Args:
        base: Base dictionary.
        override: Override dictionary whose values take precedence.
        deep: If True, perform a deep (recursive) merge (default: False).

    Returns:
        A new dictionary representing the merged result.
    """
    if deep:
        return _deep_merge(base, override)
    return {**base, **override}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def deep_update(
    target: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    """Deep-update target in-place with values from source.

    Nested dictionaries are updated recursively. Unlike a shallow
    update, keys at any depth are merged rather than replaced.

    Args:
        target: Dictionary to update in-place.
        source: Dictionary whose values will be merged into target.

    Returns:
        The same target dictionary (modified in-place).
    """
    for key, value in source.items():
        if (
            key in target
            and isinstance(target[key], dict)
            and isinstance(value, dict)
        ):
            deep_update(target[key], value)
        else:
            target[key] = value
    return target
