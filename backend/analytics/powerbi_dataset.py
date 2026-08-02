"""VisionOps AI — Power BI Dataset Preparation.

This module transforms VisionOps analytics into clean, deterministic,
tabular datasets suitable for Power BI ingestion/export.

Logical tables produced:

* ``Videos`` — video metadata.
* ``Detections`` — flattened detection records (bounding box columns
  ``bbox_x``/``bbox_y``/``bbox_w``/``bbox_h``).
* ``Events`` — business-event records.
* ``Alerts`` — alert records.
* ``KPIs`` — KPI records.
* ``Analytics`` — aggregated-analytics records.

Power BI output guarantees:

* stable column names,
* deterministic ordering,
* scalar values only,
* clean UTC ISO-8601 datetimes,
* no Python enums,
* no nested ``BoundingBox`` objects,
* no NaN / Infinity unless intentionally supported,
* no arbitrary Python objects.

Architecture rule:

This module **prepares data only**.  It does not authenticate with
Microsoft, call Power BI REST APIs, publish dashboards, manage accounts,
or contain credentials.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Mapping

from backend.exceptions import ValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column definitions (stable, deterministic order)
# ---------------------------------------------------------------------------

_VIDEO_COLUMNS: tuple[str, ...] = (
    "video_id",
    "filename",
    "file_size",
    "content_type",
    "status",
    "duration_seconds",
    "total_frames",
    "fps",
    "created_at",
    "updated_at",
)

_DETECTION_COLUMNS: tuple[str, ...] = (
    "detection_id",
    "video_id",
    "frame_number",
    "class_name",
    "confidence",
    "bbox_x",
    "bbox_y",
    "bbox_w",
    "bbox_h",
    "track_id",
    "created_at",
)

_EVENT_COLUMNS: tuple[str, ...] = (
    "event_id",
    "video_id",
    "event_type",
    "description",
    "severity",
    "source",
    "created_at",
    "updated_at",
)

_ALERT_COLUMNS: tuple[str, ...] = (
    "alert_id",
    "video_id",
    "severity",
    "message",
    "acknowledged",
    "escalated",
    "escalation_level",
    "source",
    "created_at",
    "updated_at",
)

_KPI_COLUMNS: tuple[str, ...] = (
    "kpi_id",
    "video_id",
    "metric",
    "value",
    "unit",
    "timestamp",
)

_ANALYTICS_COLUMNS: tuple[str, ...] = (
    "analytics_id",
    "video_id",
    "metric",
    "value",
    "unit",
    "period_start",
    "period_end",
    "created_at",
)

#: Mapping of table name → ordered column list.
_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "Videos": _VIDEO_COLUMNS,
    "Detections": _DETECTION_COLUMNS,
    "Events": _EVENT_COLUMNS,
    "Alerts": _ALERT_COLUMNS,
    "KPIs": _KPI_COLUMNS,
    "Analytics": _ANALYTICS_COLUMNS,
}

# ---------------------------------------------------------------------------
# PowerBIDataset container
# ---------------------------------------------------------------------------


class PowerBIDataset:
    """A deterministic, serialisable collection of Power BI tables.

    Attributes:
        tables: Mapping from table name to list of row dictionaries.
        generated_at: UTC ISO-8601 generation timestamp.
    """

    def __init__(
        self,
        tables: Mapping[str, list[dict[str, Any]]] | None = None,
        *,
        generated_at: str | None = None,
    ) -> None:
        """Initialise a Power BI dataset.

        Args:
            tables: Mapping from table name to row dictionaries.
            generated_at: Optional generation timestamp (UTC ISO-8601).
        """
        self.tables: dict[str, list[dict[str, Any]]] = {}
        if tables:
            for name, rows in tables.items():
                self.tables[name] = list(rows)
        self.generated_at = generated_at or _now_iso()

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def table_names(self) -> list[str]:
        """Return the ordered table names present in the dataset."""
        return [
            name for name in _TABLE_COLUMNS if name in self.tables
        ]

    def table(self, name: str) -> list[dict[str, Any]]:
        """Return the rows for a named table (``[]`` if absent).

        Args:
            name: Table name (e.g. ``"Detections"``).

        Returns:
            Row list for the table.
        """
        return self.tables.get(name, [])

    def to_dict(self) -> dict[str, Any]:
        """Return the dataset as a plain, JSON-serialisable dictionary.

        Returns:
            Dictionary with ``generated_at`` and one key per table.
        """
        data: dict[str, Any] = {"generated_at": self.generated_at}
        for name, rows in self.tables.items():
            data[name] = rows
        return data

    def to_json(self, indent: int | None = 2) -> str:
        """Serialise the dataset to a JSON string.

        Args:
            indent: Pretty-print indent (``None`` for compact).

        Returns:
            JSON string of the dataset.
        """
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=True)

    def to_csv(self, table_name: str) -> str:
        """Serialise a single table to a CSV string.

        Args:
            table_name: Table name (e.g. ``"Detections"``).

        Returns:
            CSV string with the table's stable column ordering.

        Raises:
            ValidationError: If the table name is unknown.
        """
        columns = _TABLE_COLUMNS.get(table_name)
        if columns is None:
            raise ValidationError(
                f"Unknown Power BI table '{table_name}'. "
                f"Available: {', '.join(_TABLE_COLUMNS)}."
            )

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(columns))
        writer.writeheader()
        for row in self.table(table_name):
            writer.writerow({col: row.get(col) for col in columns})
        return buffer.getvalue()


# ---------------------------------------------------------------------------
# PowerBIDatasetBuilder
# ---------------------------------------------------------------------------


class PowerBIDatasetBuilder:
    """Builds Power BI tabular datasets from VisionOps records.

    Args:
        datetime_keys: Column names whose values should be normalised to
            UTC ISO-8601 strings.
    """

    def __init__(
        self,
        *,
        datetime_keys: tuple[str, ...] = (
            "created_at",
            "updated_at",
            "acknowledged_at",
            "processing_started_at",
            "processing_completed_at",
            "period_start",
            "period_end",
            "timestamp",
        ),
    ) -> None:
        """Initialise the Power BI dataset builder."""
        self._datetime_keys = datetime_keys

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(
        self,
        *,
        videos: Iterable[dict[str, Any]] | None = None,
        detections: Iterable[dict[str, Any]] | None = None,
        events: Iterable[dict[str, Any]] | None = None,
        alerts: Iterable[dict[str, Any]] | None = None,
        kpis: Iterable[dict[str, Any]] | None = None,
        analytics: Iterable[dict[str, Any]] | None = None,
    ) -> PowerBIDataset:
        """Build a Power BI dataset from source records.

        Args:
            videos: Video metadata records.
            detections: Detection records.
            events: Business-event records.
            alerts: Alert records.
            kpis: KPI records.
            analytics: Aggregated-analytics records.

        Returns:
            A :class:`PowerBIDataset` with clean tabular tables.
        """
        tables: dict[str, list[dict[str, Any]]] = {}

        if videos is not None:
            tables["Videos"] = self._build_video_rows(videos)
        if detections is not None:
            tables["Detections"] = self._build_detection_rows(detections)
        if events is not None:
            tables["Events"] = self._build_event_rows(events)
        if alerts is not None:
            tables["Alerts"] = self._build_alert_rows(alerts)
        if kpis is not None:
            tables["KPIs"] = self._build_kpi_rows(kpis)
        if analytics is not None:
            tables["Analytics"] = self._build_analytics_rows(analytics)

        logger.info(
            "Power BI dataset built: %s.",
            ", ".join(f"{name}={len(rows)}" for name, rows in tables.items())
            or "empty",
        )
        return PowerBIDataset(tables)

    # ------------------------------------------------------------------
    # Table builders
    # ------------------------------------------------------------------

    def _build_video_rows(
        self,
        videos: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build the Videos table."""
        rows: list[dict[str, Any]] = []
        for record in _iter_records(videos):
            row: dict[str, Any] = {}
            for col in _VIDEO_COLUMNS:
                if col in record:
                    row[col] = self._clean_value(record[col], col=col)
            rows.append(row)
        return _sort_rows(rows, "video_id")

    def _build_detection_rows(
        self,
        detections: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build the Detections table with flattened bbox columns."""
        rows: list[dict[str, Any]] = []
        for record in _iter_records(detections):
            row: dict[str, Any] = {}
            for col in _DETECTION_COLUMNS:
                if col in record:
                    row[col] = self._clean_value(record[col], col=col)
            rows.append(row)
        return _sort_rows(rows, "detection_id")

    def _build_event_rows(
        self,
        events: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build the Events table."""
        rows: list[dict[str, Any]] = []
        for record in _iter_records(events):
            row: dict[str, Any] = {}
            for col in _EVENT_COLUMNS:
                if col in record:
                    row[col] = self._clean_value(record[col], col=col)
            rows.append(row)
        return _sort_rows(rows, "event_id")

    def _build_alert_rows(
        self,
        alerts: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build the Alerts table."""
        rows: list[dict[str, Any]] = []
        for record in _iter_records(alerts):
            row: dict[str, Any] = {}
            for col in _ALERT_COLUMNS:
                if col in record:
                    row[col] = self._clean_value(record[col], col=col)
            rows.append(row)
        return _sort_rows(rows, "alert_id")

    def _build_kpi_rows(
        self,
        kpis: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build the KPIs table."""
        rows: list[dict[str, Any]] = []
        for record in _iter_records(kpis):
            row: dict[str, Any] = {}
            for col in _KPI_COLUMNS:
                if col in record:
                    row[col] = self._clean_value(record[col], col=col)
            rows.append(row)
        return _sort_rows(rows, "kpi_id")

    def _build_analytics_rows(
        self,
        analytics: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build the Analytics table."""
        rows: list[dict[str, Any]] = []
        for record in _iter_records(analytics):
            row: dict[str, Any] = {}
            for col in _ANALYTICS_COLUMNS:
                if col in record:
                    row[col] = self._clean_value(record[col], col=col)
            rows.append(row)
        return _sort_rows(rows, "analytics_id")

    # ------------------------------------------------------------------
    # Value cleaning
    # ------------------------------------------------------------------

    def _clean_value(self, value: Any, *, col: str) -> Any:
        """Normalise a single value for Power BI output.

        * datetimes → UTC ISO-8601 strings,
        * enums → string values,
        * finite numbers → plain ``int``/``float``,
        * strings → whitespace-stripped,
        * NaN/Infinity → ``None`` (never emitted),
        * lists/tuples (e.g. nested bbox) → JSON string representation,
        * all other scalars → as-is.

        Args:
            value: Raw value.
            col: Column name (used for diagnostics).

        Returns:
            A Power BI-safe scalar value.
        """
        # Enums first (must be resolved before other checks).
        if isinstance(value, Enum):
            return value.value

        if value is None:
            return None

        if isinstance(value, bool):
            return value

        if isinstance(value, datetime):
            return _to_utc_iso(value)

        if isinstance(value, str):
            if col in self._datetime_keys and _looks_like_timestamp(value):
                try:
                    return _to_utc_iso(value)
                except ValidationError:
                    return value
            return value.strip()

        if isinstance(value, (int, float)):
            if isinstance(value, float) and not math.isfinite(value):
                logger.debug(
                    "Rejected non-finite value for Power BI column '%s'.",
                    col,
                )
                return None
            return value

        if isinstance(value, (list, tuple)):
            # Flatten simple [x, y, w, h] boxes are handled by the column
            # mapping; any other sequence is serialised as JSON.
            return json.dumps([_scalarize(v) for v in value])

        if isinstance(value, dict):
            return json.dumps({k: _scalarize(v) for k, v in value.items()})

        # Fallback: scalarise unknown objects.
        scalarized = _scalarize(value)
        if scalarized is None:
            logger.debug(
                "Rejected non-scalar value for Power BI column '%s'.",
                col,
            )
        return scalarized


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _iter_records(records: Iterable[dict[str, Any]]) -> Iterable[dict[str, Any]]:
    """Yield only dict records from an iterable."""
    for record in records:
        if isinstance(record, dict):
            yield record


def _sort_rows(
    rows: list[dict[str, Any]],
    key: str,
) -> list[dict[str, Any]]:
    """Return rows sorted by a string column (stable, deterministic)."""
    return sorted(
        rows,
        key=lambda r: (r.get(key) is None, str(r.get(key, ""))),
    )


def _to_utc_iso(value: Any) -> str:
    """Normalise a datetime-like value to a UTC ISO-8601 string."""
    parsed: datetime
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(
                f"Invalid ISO-8601 timestamp: {value!r}."
            ) from exc
    else:
        raise ValidationError(
            "Timestamp must be a datetime or string, got "
            f"{type(value).__name__}."
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


def _looks_like_timestamp(value: str) -> bool:
    """Return whether a string looks like an ISO-8601 timestamp."""
    return len(value) >= 8 and ("T" in value or "-" in value[:4])


def _scalarize(value: Any) -> Any:
    """Best-effort conversion of an arbitrary value to a scalar."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return _to_utc_iso(value)
    if isinstance(value, (list, tuple)):
        return [_scalarize(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _scalarize(v) for k, v in value.items()}
    try:
        return str(value)
    except Exception:  # pragma: no cover - defensive
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["PowerBIDataset", "PowerBIDatasetBuilder", "TABLE_COLUMNS"]

#: Public alias for stable column definitions.
TABLE_COLUMNS: dict[str, tuple[str, ...]] = dict(_TABLE_COLUMNS)

