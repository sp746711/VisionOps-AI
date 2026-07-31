"""VisionOps AI — Config-aware CSV storage manager.

Provides a high-level interface to every CSV-backed data store used in
the VisionOps AI backend (videos, detections, events, alerts, KPIs,
analytics).  Built on top of ``backend.utils.csv_utils``.

Usage::

    from backend.storage.csv_manager import CSVManager

    mgr = CSVManager()
    dfg = mgr.read_detections()
    mgr.append_video({"id": "abc", "filename": "clip.mp4"})
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Sequence

from backend.core.config import settings
from backend.exceptions import CSVError
from backend.utils.csv_utils import (
    append_rows,
    backup_csv,
    check_headers,
    csv_exists,
    export_csv,
    read_csv,
    update_rows,
    validate_csv,
    write_csv,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_DELIMITER: str = ","
_DEFAULT_ENCODING: str = "utf-8"

# ---------------------------------------------------------------------------
# CSV data-store descriptors
# ---------------------------------------------------------------------------

_CSV_STORES: dict[str, dict[str, Any]] = {
    "videos": {
        "path_key": "VIDEOS_CSV",
        "description": "Video metadata",
    },
    "detections": {
        "path_key": "DETECTIONS_CSV",
        "description": "Detection results",
    },
    "events": {
        "path_key": "EVENTS_CSV",
        "description": "Business events",
    },
    "alerts": {
        "path_key": "ALERTS_CSV",
        "description": "Alert records",
    },
    "kpis": {
        "path_key": "KPIS_CSV",
        "description": "Key performance indicators",
    },
    "analytics": {
        "path_key": "ANALYTICS_CSV",
        "description": "Aggregated analytics",
    },
}


# ---------------------------------------------------------------------------
# CSVManager
# ---------------------------------------------------------------------------


class CSVManager:
    """Config-aware manager for all CSV-backed data stores.

    Each named store (``videos``, ``detections``, ``events``, ``alerts``,
    ``kpis``, ``analytics``) is resolved through the global ``settings``
    object so paths remain consistent across the application.

    The manager delegates actual I/O to the low-level helpers in
    ``backend.utils.csv_utils``.

    Raises:
        CSVError: Wraps any underlying I/O or parsing error.
    """

    def __init__(
        self,
        delimiter: str = _DEFAULT_DELIMITER,
        encoding: str = _DEFAULT_ENCODING,
    ) -> None:
        """Initialise the CSV manager.

        Args:
            delimiter: Field delimiter for CSV files (default: ``,``).
            encoding: File encoding (default: ``utf-8``).
        """
        self._delimiter = delimiter
        self._encoding = encoding

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    def _store_path(self, store_name: str) -> Path:
        """Resolve the absolute path for a named CSV store.

        Args:
            store_name: One of ``videos``, ``detections``, ``events``,
                ``alerts``, ``kpis``, ``analytics``.

        Returns:
            Resolved absolute ``Path`` to the CSV file.

        Raises:
            CSVError: If *store_name* is unknown.
        """
        descriptor = _CSV_STORES.get(store_name)
        if descriptor is None:
            raise CSVError(
                f"Unknown CSV store '{store_name}'. "
                f"Available: {list(_CSV_STORES)}"
            )
        return Path(getattr(settings, descriptor["path_key"]))

    def store_names(self) -> list[str]:
        """Return the list of recognised CSV store names.

        Returns:
            Sorted list of store name strings.
        """
        return sorted(_CSV_STORES)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def read_store(
        self,
        store_name: str,
    ) -> list[dict[str, str]]:
        """Read every row from a CSV data store.

        Args:
            store_name: Named CSV store to read.

        Returns:
            List of row dictionaries keyed by header names.

        Raises:
            CSVError: If the file is missing, empty, or malformed.
        """
        path = self._store_path(store_name)
        try:
            return read_csv(path, delimiter=self._delimiter, encoding=self._encoding)
        except (FileNotFoundError, ValueError) as exc:
            raise CSVError(
                f"Failed to read {store_name} from {path}: {exc}"
            ) from exc

    def read_videos(self) -> list[dict[str, str]]:
        """Convenience: read the videos CSV store."""
        return self.read_store("videos")

    def read_detections(self) -> list[dict[str, str]]:
        """Convenience: read the detections CSV store."""
        return self.read_store("detections")

    def read_events(self) -> list[dict[str, str]]:
        """Convenience: read the events CSV store."""
        return self.read_store("events")

    def read_alerts(self) -> list[dict[str, str]]:
        """Convenience: read the alerts CSV store."""
        return self.read_store("alerts")

    def read_kpis(self) -> list[dict[str, str]]:
        """Convenience: read the KPIs CSV store."""
        return self.read_store("kpis")

    def read_analytics(self) -> list[dict[str, str]]:
        """Convenience: read the analytics CSV store."""
        return self.read_store("analytics")

    # ------------------------------------------------------------------
    # Write (overwrite)
    # ------------------------------------------------------------------

    def write_store(
        self,
        store_name: str,
        data: Sequence[dict[str, Any]],
        fieldnames: Sequence[str] | None = None,
    ) -> Path:
        """Overwrite a CSV data store with new data (atomic write).

        Args:
            store_name: Named CSV store to write.
            data: List of dictionaries to persist.
            fieldnames: Column order.  If ``None``, inferred from first
                dict keys.

        Returns:
            Resolved ``Path`` of the written file.

        Raises:
            CSVError: On write failure.
        """
        path = self._store_path(store_name)
        try:
            return write_csv(
                path,
                data,
                fieldnames=fieldnames,
                delimiter=self._delimiter,
                encoding=self._encoding,
            )
        except (OSError, ValueError) as exc:
            raise CSVError(
                f"Failed to write {store_name} to {path}: {exc}"
            ) from exc

    def write_videos(
        self,
        data: Sequence[dict[str, Any]],
        fieldnames: Sequence[str] | None = None,
    ) -> Path:
        """Convenience: overwrite the videos CSV store."""
        return self.write_store("videos", data, fieldnames=fieldnames)

    def write_detections(
        self,
        data: Sequence[dict[str, Any]],
        fieldnames: Sequence[str] | None = None,
    ) -> Path:
        """Convenience: overwrite the detections CSV store."""
        return self.write_store("detections", data, fieldnames=fieldnames)

    def write_events(
        self,
        data: Sequence[dict[str, Any]],
        fieldnames: Sequence[str] | None = None,
    ) -> Path:
        """Convenience: overwrite the events CSV store."""
        return self.write_store("events", data, fieldnames=fieldnames)

    def write_alerts(
        self,
        data: Sequence[dict[str, Any]],
        fieldnames: Sequence[str] | None = None,
    ) -> Path:
        """Convenience: overwrite the alerts CSV store."""
        return self.write_store("alerts", data, fieldnames=fieldnames)

    def write_kpis(
        self,
        data: Sequence[dict[str, Any]],
        fieldnames: Sequence[str] | None = None,
    ) -> Path:
        """Convenience: overwrite the KPIs CSV store."""
        return self.write_store("kpis", data, fieldnames=fieldnames)

    def write_analytics(
        self,
        data: Sequence[dict[str, Any]],
        fieldnames: Sequence[str] | None = None,
    ) -> Path:
        """Convenience: overwrite the analytics CSV store."""
        return self.write_store("analytics", data, fieldnames=fieldnames)

    # ------------------------------------------------------------------
    # Append
    # ------------------------------------------------------------------

    def append_store(
        self,
        store_name: str,
        rows: Sequence[dict[str, Any]],
    ) -> Path:
        """Append rows to an existing CSV data store.

        Args:
            store_name: Named CSV store to append to.
            rows: List of dictionaries to append.

        Returns:
            Resolved ``Path`` of the file that was appended to.

        Raises:
            CSVError: If the store file does not exist or append fails.
        """
        path = self._store_path(store_name)
        try:
            return append_rows(
                path,
                rows,
                delimiter=self._delimiter,
                encoding=self._encoding,
            )
        except (OSError, ValueError) as exc:
            raise CSVError(
                f"Failed to append to {store_name} ({path}): {exc}"
            ) from exc

    def append_videos(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> Path:
        """Convenience: append rows to the videos CSV store."""
        return self.append_store("videos", rows)

    def append_detections(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> Path:
        """Convenience: append rows to the detections CSV store."""
        return self.append_store("detections", rows)

    def append_events(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> Path:
        """Convenience: append rows to the events CSV store."""
        return self.append_store("events", rows)

    def append_alerts(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> Path:
        """Convenience: append rows to the alerts CSV store."""
        return self.append_store("alerts", rows)

    def append_kpis(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> Path:
        """Convenience: append rows to the KPIs CSV store."""
        return self.append_store("kpis", rows)

    def append_analytics(
        self,
        rows: Sequence[dict[str, Any]],
    ) -> Path:
        """Convenience: append rows to the analytics CSV store."""
        return self.append_store("analytics", rows)

    # ------------------------------------------------------------------
    # Update (in-place)
    # ------------------------------------------------------------------

    def update_rows(
        self,
        store_name: str,
        match_fn: Any,
        update_fn: Any,
    ) -> int:
        """Update rows in a CSV store that satisfy a predicate.

        The file is rewritten atomically after modification.

        Args:
            store_name: Named CSV store to update.
            match_fn: Callable that receives a row dict and returns
                ``True`` if the row should be updated.
            update_fn: Callable that receives a row dict and returns the
                updated row dict.

        Returns:
            Number of rows updated.

        Raises:
            CSVError: If reading or writing fails.
        """
        path = self._store_path(store_name)
        try:
            return update_rows(
                path,
                match_fn,
                update_fn,
                delimiter=self._delimiter,
                encoding=self._encoding,
            )
        except (OSError, ValueError) as exc:
            raise CSVError(
                f"Failed to update rows in {store_name} ({path}): {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_store(
        self,
        store_name: str,
        expected_headers: Sequence[str] | None = None,
    ) -> bool:
        """Validate that a CSV data store is well-formed.

        Args:
            store_name: Named CSV store to validate.
            expected_headers: Optional set of headers that must be
                present.

        Returns:
            ``True`` if valid.

        Raises:
            CSVError: If the file is missing, empty, or malformed.
        """
        path = self._store_path(store_name)
        try:
            return validate_csv(
                path,
                expected_headers=expected_headers,
                delimiter=self._delimiter,
                encoding=self._encoding,
            )
        except (FileNotFoundError, ValueError) as exc:
            raise CSVError(
                f"Validation failed for {store_name} ({path}): {exc}"
            ) from exc

    def check_headers(
        self,
        store_name: str,
        expected_headers: Sequence[str],
    ) -> bool:
        """Check that a CSV store contains all required headers.

        Args:
            store_name: Named CSV store to check.
            expected_headers: Headers that must be present.

        Returns:
            ``True`` if all expected headers are present.

        Raises:
            CSVError: If the file cannot be read.
        """
        path = self._store_path(store_name)
        try:
            return check_headers(
                path,
                expected_headers,
                delimiter=self._delimiter,
                encoding=self._encoding,
            )
        except (FileNotFoundError, ValueError) as exc:
            raise CSVError(
                f"Header check failed for {store_name} ({path}): {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Existence
    # ------------------------------------------------------------------

    def store_exists(self, store_name: str) -> bool:
        """Check whether a CSV data store file exists and is non-empty.

        Args:
            store_name: Named CSV store.

        Returns:
            ``True`` if the file exists and is non-empty.
        """
        path = self._store_path(store_name)
        return csv_exists(path)

    # ------------------------------------------------------------------
    # Backup
    # ------------------------------------------------------------------

    def backup_store(
        self,
        store_name: str,
        backup_dir: str | Path | None = None,
    ) -> Path:
        """Create a timestamped backup of a CSV data store.

        Args:
            store_name: Named CSV store to back up.
            backup_dir: Target directory.  If ``None``, uses the same
                directory as the source file.

        Returns:
            ``Path`` of the backup file.

        Raises:
            CSVError: If the source does not exist or backup fails.
        """
        path = self._store_path(store_name)
        try:
            return backup_csv(path, backup_dir=backup_dir)
        except (FileNotFoundError, OSError) as exc:
            raise CSVError(
                f"Backup failed for {store_name} ({path}): {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------

    def store_info(self, store_name: str) -> dict[str, Any]:
        """Return metadata about a CSV data store.

        Args:
            store_name: Named CSV store.

        Returns:
            Dictionary with keys ``name``, ``path``, ``description``,
            ``exists``, ``size_bytes`` (``None`` if file missing).
        """
        path = self._store_path(store_name)
        descriptor = _CSV_STORES.get(store_name, {})
        exists = path.is_file()
        return {
            "name": store_name,
            "path": str(path),
            "description": descriptor.get("description", ""),
            "exists": exists,
            "size_bytes": path.stat().st_size if exists else None,
        }

