"""VisionOps AI — Config-aware JSON storage manager.

Provides a high-level interface to JSON-backed data files used in the
VisionOps AI backend (summary data and any future JSON stores).  Built
on top of ``backend.utils.json_utils``.

Usage::

    from backend.storage.json_manager import JSONManager

    mgr = JSONManager()
    summary = mgr.read_summary()
    mgr.write_summary({"total_videos": 42, ...})
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.exceptions import JSONError
from backend.utils.json_utils import (
    deep_update,
    handle_malformed_json,
    merge_json,
    pretty_print,
    read_json,
    safe_deserialize,
    safe_serialize,
    validate_json,
    write_json,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_ENCODING: str = "utf-8"
_DEFAULT_INDENT: int = 2

# ---------------------------------------------------------------------------
# JSON data-store descriptors
# ---------------------------------------------------------------------------

_JSON_STORES: dict[str, dict[str, Any]] = {
    "summary": {
        "path_key": "SUMMARY_JSON",
        "description": "Aggregated summary data",
    },
}


# ---------------------------------------------------------------------------
# JSONManager
# ---------------------------------------------------------------------------


class JSONManager:
    """Config-aware manager for JSON-backed data files.

    Each named store (``summary`` and any future additions) is resolved
    through the global ``settings`` object to maintain path consistency
    across the application.

    The manager delegates actual I/O to the low-level helpers in
    ``backend.utils.json_utils``.

    Raises:
        JSONError: Wraps any underlying I/O, encoding, or serialisation
            error.
    """

    def __init__(
        self,
        encoding: str = _DEFAULT_ENCODING,
        indent: int | None = _DEFAULT_INDENT,
    ) -> None:
        """Initialise the JSON manager.

        Args:
            encoding: File encoding (default: ``utf-8``).
            indent: Pretty-print indent level (default: ``2``).  Pass
                ``None`` for compact output.
        """
        self._encoding = encoding
        self._indent = indent

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    def _store_path(self, store_name: str) -> Path:
        """Resolve the absolute path for a named JSON store.

        Args:
            store_name: One of ``summary`` (or future stores).

        Returns:
            Resolved absolute ``Path`` to the JSON file.

        Raises:
            JSONError: If *store_name* is unknown.
        """
        descriptor = _JSON_STORES.get(store_name)
        if descriptor is None:
            raise JSONError(
                f"Unknown JSON store '{store_name}'. "
                f"Available: {list(_JSON_STORES)}"
            )
        return Path(getattr(settings, descriptor["path_key"]))

    def store_names(self) -> list[str]:
        """Return the list of recognised JSON store names.

        Returns:
            Sorted list of store name strings.
        """
        return sorted(_JSON_STORES)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def read_store(self, store_name: str) -> Any:
        """Read and deserialize a JSON data store.

        Args:
            store_name: Named JSON store to read.

        Returns:
            Deserialized Python object (typically a ``dict`` or ``list``).

        Raises:
            JSONError: If the file is missing or malformed.
        """
        path = self._store_path(store_name)
        try:
            return read_json(path, encoding=self._encoding)
        except (FileNotFoundError, ValueError) as exc:
            raise JSONError(
                f"Failed to read {store_name} from {path}: {exc}"
            ) from exc

    def read_summary(self) -> Any:
        """Convenience: read the summary JSON store (``data/summary.json``).

        Returns:
            Deserialized summary data.
        """
        return self.read_store("summary")

    # ------------------------------------------------------------------
    # Write (overwrite)
    # ------------------------------------------------------------------

    def write_store(
        self,
        store_name: str,
        data: Any,
        sort_keys: bool = False,
    ) -> Path:
        """Serialize data and write to a JSON data store (atomic write).

        Args:
            store_name: Named JSON store to write.
            data: Data to serialize.
            sort_keys: Sort dictionary keys in output (default: ``False``).

        Returns:
            Resolved ``Path`` of the written file.

        Raises:
            JSONError: On serialisation or write failure.
        """
        path = self._store_path(store_name)
        try:
            return write_json(
                path,
                data,
                indent=self._indent,
                encoding=self._encoding,
                sort_keys=sort_keys,
            )
        except (OSError, ValueError) as exc:
            raise JSONError(
                f"Failed to write {store_name} to {path}: {exc}"
            ) from exc

    def write_summary(
        self,
        data: Any,
        sort_keys: bool = False,
    ) -> Path:
        """Convenience: overwrite the summary JSON store.

        Args:
            data: Summary data to persist.
            sort_keys: Sort dictionary keys in output (default: ``False``).

        Returns:
            Resolved ``Path`` of the written file.
        """
        return self.write_store("summary", data, sort_keys=sort_keys)

    # ------------------------------------------------------------------
    # Existence
    # ------------------------------------------------------------------

    def store_exists(self, store_name: str) -> bool:
        """Check whether a JSON data store file exists and is non-empty.

        Args:
            store_name: Named JSON store.

        Returns:
            ``True`` if the file exists, is a regular file, and is
            non-empty.
        """
        path = self._store_path(store_name)
        return path.is_file() and path.stat().st_size > 0

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_store(self, store_name: str) -> bool:
        """Validate that a JSON data store file contains valid JSON.

        Args:
            store_name: Named JSON store to validate.

        Returns:
            ``True`` if the file is valid JSON.

        Raises:
            JSONError: If the file cannot be read.
        """
        path = self._store_path(store_name)
        try:
            return validate_json(path)
        except (OSError, ValueError) as exc:
            raise JSONError(
                f"Validation failed for {store_name} ({path}): {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Repair
    # ------------------------------------------------------------------

    def read_with_repair(
        self,
        store_name: str,
    ) -> Any:
        """Read a JSON data store, attempting to repair malformed content.

        Args:
            store_name: Named JSON store.

        Returns:
            Deserialized data (repaired if necessary).

        Raises:
            JSONError: If the file is missing or cannot be repaired.
        """
        path = self._store_path(store_name)
        try:
            return handle_malformed_json(
                path,
                repair_attempts=True,
                encoding=self._encoding,
            )
        except (FileNotFoundError, ValueError) as exc:
            raise JSONError(
                f"Failed to read/repair {store_name} ({path}): {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Merge helpers
    # ------------------------------------------------------------------

    def merge_into_store(
        self,
        store_name: str,
        override: dict[str, Any],
        deep: bool = False,
    ) -> Path:
        """Read a JSON store, merge data into it, and write back.

        Args:
            store_name: Named JSON store.
            override: Dictionary whose values take precedence.
            deep: If ``True``, perform a recursive deep merge (default:
                ``False``).

        Returns:
            Resolved ``Path`` of the written file.

        Raises:
            JSONError: If the store does not exist or any operation fails.
        """
        current = self.read_store(store_name)
        if not isinstance(current, dict):
            raise JSONError(
                f"Cannot merge into {store_name}: existing data is not "
                f"a dictionary (got {type(current).__name__})."
            )
        if not isinstance(override, dict):
            raise JSONError(
                f"Cannot merge into {store_name}: override data must be "
                f"a dictionary (got {type(override).__name__})."
            )
        merged = merge_json(current, override, deep=deep)
        return self.write_store(store_name, merged)

    def deep_update_store(
        self,
        store_name: str,
        source: dict[str, Any],
    ) -> Path:
        """Deep-update a JSON store in-place with values from *source*.

        Reads the store, applies a recursive deep update, and writes it
        back atomically.

        Args:
            store_name: Named JSON store.
            source: Dictionary whose values will be merged recursively.

        Returns:
            Resolved ``Path`` of the written file.

        Raises:
            JSONError: If the store does not exist or any operation fails.
        """
        current = self.read_store(store_name)
        if not isinstance(current, dict):
            raise JSONError(
                f"Cannot deep-update {store_name}: existing data is not "
                f"a dictionary (got {type(current).__name__})."
            )
        if not isinstance(source, dict):
            raise JSONError(
                f"Cannot deep-update {store_name}: source data must be "
                f"a dictionary (got {type(source).__name__})."
            )
        deep_update(current, source)
        return self.write_store(store_name, current)

    # ------------------------------------------------------------------
    # Safe serialisation helpers
    # ------------------------------------------------------------------

    def safe_serialize(
        self,
        obj: Any,
        indent: int | None = None,
    ) -> str:
        """Safely serialize a Python object to a JSON string.

        Non-serializable types are converted via ``str()``.

        Args:
            obj: Object to serialize.
            indent: Optional indent level for pretty-printing.

        Returns:
            JSON string.
        """
        return safe_serialize(obj, indent=indent)

    def safe_deserialize(self, json_str: str, default: Any = None) -> Any:
        """Safely deserialize a JSON string, returning a default on failure.

        Args:
            json_str: JSON string to deserialize.
            default: Value to return on failure (default: ``None``).

        Returns:
            Deserialized object or *default*.
        """
        return safe_deserialize(json_str, default=default)

    def pretty_print(self, data: Any, sort_keys: bool = False) -> str:
        """Return a pretty-printed JSON string of *data*.

        Args:
            data: Data to format.
            sort_keys: Sort dictionary keys (default: ``False``).

        Returns:
            Formatted JSON string.
        """
        return pretty_print(data, indent=self._indent, sort_keys=sort_keys)

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def store_info(self, store_name: str) -> dict[str, Any]:
        """Return metadata about a JSON data store.

        Args:
            store_name: Named JSON store.

        Returns:
            Dictionary with keys ``name``, ``path``, ``description``,
            ``exists``, ``size_bytes`` (``None`` if file missing).
        """
        path = self._store_path(store_name)
        descriptor = _JSON_STORES.get(store_name, {})
        exists = path.is_file()
        return {
            "name": store_name,
            "path": str(path),
            "description": descriptor.get("description", ""),
            "exists": exists,
            "size_bytes": path.stat().st_size if exists else None,
        }

