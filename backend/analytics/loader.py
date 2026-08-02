"""VisionOps AI — Analytics Data Loading.

This module implements the analytics data-loading layer.  It loads the
raw analytics source stores (videos, detections, events, alerts, KPIs,
analytics) through the existing storage abstraction
(:class:`~backend.storage.StorageService`) and normalises them into
analytics-compatible structures.

Design rules:

* The loader reuses ``StorageService`` — it never parses CSV/JSON
  directly.
* Missing or empty stores are treated as *legitimate empty datasets*
  (``[]``); genuine storage failures are re-raised as
  :class:`~backend.exceptions.StorageError`.
* Optional filtering by video IDs and an inclusive date range is
  supported.
* The loader is dependency-injectable so tests can use mocked storage.

Usage::

    from backend.analytics import AnalyticsLoader

    loader = AnalyticsLoader(storage_service=storage)
    data = loader.load_all(filters={"video_ids": ["vid_001"]})
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from backend.exceptions import StorageError, ValidationError
from backend.storage import StorageService

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Public data containers
# ---------------------------------------------------------------------------

_DATE_PATTERN_LEN: int = 10


@dataclass(slots=True)
class AnalyticsFilters:
    """Optional filters applied while loading analytics source data.

    Attributes:
        video_ids: Optional list of video IDs to scope the load.
        date_from: Optional inclusive start date (``YYYY-MM-DD``).
        date_to: Optional inclusive end date (``YYYY-MM-DD``).
    """

    video_ids: list[str] | None = None
    date_from: str | None = None
    date_to: str | None = None

    @classmethod
    def from_dict(cls, filters: dict[str, Any] | None) -> "AnalyticsFilters":
        """Build a filter object from a plain dictionary.

        Args:
            filters: Optional filter mapping with keys ``video_ids``,
                ``date_from`` and ``date_to``.

        Returns:
            A new :class:`AnalyticsFilters` instance.

        Raises:
            ValidationError: If a date is provided without the expected
                ``YYYY-MM-DD`` format.
        """
        if not filters:
            return cls()

        raw_videos = filters.get("video_ids")
        video_ids: list[str] | None = None
        if isinstance(raw_videos, (list, tuple)) and raw_videos:
            video_ids = [str(v) for v in raw_videos if str(v).strip()]

        date_from = filters.get("date_from")
        date_to = filters.get("date_to")

        normalized_from = cls._normalize_date(date_from, "date_from")
        normalized_to = cls._normalize_date(date_to, "date_to")

        return cls(
            video_ids=video_ids,
            date_from=normalized_from,
            date_to=normalized_to,
        )

    @staticmethod
    def _normalize_date(value: Any, field_name: str) -> str | None:
        """Validate and normalize an optional ``YYYY-MM-DD`` date value.

        Args:
            value: Raw filter value.
            field_name: Field name used in error messages.

        Returns:
            The stripped date string, or ``None`` when *value* is empty.

        Raises:
            ValidationError: If *value* is not empty and does not match
                the ``YYYY-MM-DD`` format.
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return None

        text = str(value).strip()
        if len(text) != _DATE_PATTERN_LEN or text[4] != "-" or text[7] != "-":
            raise ValidationError(
                f"Invalid {field_name} '{value}'. Expected format: YYYY-MM-DD."
            )
        parts = text.split("-")
        try:
            year = int(parts[0])
            month = int(parts[1])
            day = int(parts[2])
        except (ValueError, IndexError) as exc:
            raise ValidationError(
                f"Invalid {field_name} '{value}'. Expected format: YYYY-MM-DD."
            ) from exc

        if not (1 <= month <= 12) or not (1 <= day <= 31) or year < 1:
            raise ValidationError(
                f"Invalid {field_name} '{value}'. Expected format: YYYY-MM-DD."
            )
        return text


@dataclass(slots=True)
class AnalyticsSourceData:
    """Loaded analytics source records grouped by store.

    Attributes:
        videos: Video metadata records.
        detections: Detection records.
        events: Business-event records.
        alerts: Alert records.
        kpis: KPI records.
        analytics: Aggregated-analytics records.
    """

    videos: list[dict[str, Any]] = field(default_factory=list)
    detections: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    kpis: list[dict[str, Any]] = field(default_factory=list)
    analytics: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_records(self) -> int:
        """Return the total number of loaded records across all stores."""
        return (
            len(self.videos)
            + len(self.detections)
            + len(self.events)
            + len(self.alerts)
            + len(self.kpis)
            + len(self.analytics)
        )

    def to_dict(self) -> dict[str, list[dict[str, Any]]]:
        """Return the source data keyed by store name."""
        return {
            "videos": self.videos,
            "detections": self.detections,
            "events": self.events,
            "alerts": self.alerts,
            "kpis": self.kpis,
            "analytics": self.analytics,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AnalyticsSourceData":
        """Build source data from a plain dictionary.

        Args:
            data: Mapping keyed by store name to record lists.

        Returns:
            A new :class:`AnalyticsSourceData` instance.
        """
        return cls(
            videos=list(data.get("videos") or []),
            detections=list(data.get("detections") or []),
            events=list(data.get("events") or []),
            alerts=list(data.get("alerts") or []),
            kpis=list(data.get("kpis") or []),
            analytics=list(data.get("analytics") or []),
        )


# ---------------------------------------------------------------------------
# AnalyticsLoader
# ---------------------------------------------------------------------------


class AnalyticsLoader:
    """Loads analytics source data through the storage layer.

    Args:
        storage_service: Optional injected :class:`StorageService`.  When
            ``None``, a default instance is created.
    """

    #: Timestamp column used for date-range filtering per store.
    _STORE_TIMESTAMP_KEYS: dict[str, str] = {
        "videos": "created_at",
        "detections": "created_at",
        "events": "created_at",
        "alerts": "created_at",
        "kpis": "timestamp",
        "analytics": "created_at",
    }

    def __init__(self, storage_service: StorageService | None = None) -> None:
        """Initialise the analytics loader."""
        self._storage = storage_service or StorageService()
        logger.info(
            "AnalyticsLoader initialised (storage=%s)",
            type(self._storage).__name__,
        )

    # ------------------------------------------------------------------
    # Per-store loading
    # ------------------------------------------------------------------

    def load_videos(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Load video metadata records.

        Args:
            filters: Optional filter parameters.

        Returns:
            List of video record dictionaries.
        """
        return self._load_store("videos", filters)

    def load_detections(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Load detection records.

        Args:
            filters: Optional filter parameters.

        Returns:
            List of detection record dictionaries.
        """
        return self._load_store("detections", filters)

    def load_events(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Load business-event records.

        Args:
            filters: Optional filter parameters.

        Returns:
            List of event record dictionaries.
        """
        return self._load_store("events", filters)

    def load_alerts(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Load alert records.

        Args:
            filters: Optional filter parameters.

        Returns:
            List of alert record dictionaries.
        """
        return self._load_store("alerts", filters)

    def load_kpis(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Load KPI records.

        Args:
            filters: Optional filter parameters.

        Returns:
            List of KPI record dictionaries.
        """
        return self._load_store("kpis", filters)

    def load_analytics(
        self,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Load aggregated-analytics records.

        Args:
            filters: Optional filter parameters.

        Returns:
            List of analytics record dictionaries.
        """
        return self._load_store("analytics", filters)

    # ------------------------------------------------------------------
    # Aggregate loading
    # ------------------------------------------------------------------

    def load_all(
        self,
        filters: dict[str, Any] | None = None,
    ) -> AnalyticsSourceData:
        """Load every analytics source store in a single pass.

        All stores are loaded through the storage layer and filtered
        consistently.  A single load is performed per store, so callers
        should prefer this method over repeated per-store calls.

        Args:
            filters: Optional filter parameters (``video_ids``,
                ``date_from``, ``date_to``).

        Returns:
            An :class:`AnalyticsSourceData` container with all records.

        Raises:
            ValidationError: If filter dates are malformed.
            StorageError: If a store genuinely fails to load.
        """
        parsed = AnalyticsFilters.from_dict(filters)

        data = AnalyticsSourceData(
            videos=self._load_store("videos", parsed),
            detections=self._load_store("detections", parsed),
            events=self._load_store("events", parsed),
            alerts=self._load_store("alerts", parsed),
            kpis=self._load_store("kpis", parsed),
            analytics=self._load_store("analytics", parsed),
        )

        logger.info(
            "Analytics source data loaded: %d records total.",
            data.total_records,
        )
        return data

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_store(
        self,
        store_name: str,
        filters: dict[str, Any] | AnalyticsFilters | None,
    ) -> list[dict[str, Any]]:
        """Load and filter a single named store through the storage layer.

        Args:
            store_name: Named CSV store to load.
            filters: Optional filter parameters (dict or
                :class:`AnalyticsFilters`).

        Returns:
            Loaded (and filtered) record list.

        Raises:
            StorageError: If the store genuinely fails to load.
        """
        parsed = (
            filters
            if isinstance(filters, AnalyticsFilters)
            else AnalyticsFilters.from_dict(filters)
        )

        try:
            rows = self._storage.read_csv_store(store_name)
        except StorageError as exc:
            # Distinguish "legitimately no data" from "loading failed".
            # A store that does not exist or is a zero-byte placeholder is
            # an empty dataset; any other failure is re-raised.
            if self._store_unavailable(store_name):
                logger.info(
                    "Analytics store '%s' unavailable — returning empty dataset.",
                    store_name,
                )
                rows = []
            else:
                raise StorageError(
                    f"Failed to load analytics store '{store_name}': {exc}"
                ) from exc

        return self._apply_filters(store_name, rows, parsed)

    def _store_unavailable(self, store_name: str) -> bool:
        """Return ``True`` when a store file is missing or empty."""
        try:
            return not self._storage.csv_manager.store_exists(store_name)
        except StorageError:
            return True

    def _apply_filters(
        self,
        store_name: str,
        rows: list[dict[str, Any]],
        filters: AnalyticsFilters,
    ) -> list[dict[str, Any]]:
        """Apply video-ID and date-range filters to loaded records.

        Args:
            store_name: Named store the rows belong to.
            rows: Loaded row dictionaries.
            filters: Parsed filters.

        Returns:
            Filtered record list.
        """
        if not rows:
            return rows

        result: list[dict[str, Any]] = []

        for row in rows:
            if not isinstance(row, dict):
                continue
            if not self._matches_filters(store_name, row, filters):
                continue
            result.append(row)

        return result

    def _matches_filters(
        self,
        store_name: str,
        row: dict[str, Any],
        filters: AnalyticsFilters,
    ) -> bool:
        """Check whether a single row matches the active filters.

        Args:
            store_name: Named store the row belongs to.
            row: Record dictionary.
            filters: Parsed filters.

        Returns:
            ``True`` if the row should be included.
        """
        if filters.video_ids:
            video_id = str(row.get("video_id", "")).strip()
            if video_id not in filters.video_ids:
                return False

        if filters.date_from or filters.date_to:
            ts_key = self._STORE_TIMESTAMP_KEYS.get(store_name, "created_at")
            day = str(row.get(ts_key, "")).strip()[:_DATE_PATTERN_LEN]

            if not day:
                # No usable timestamp — exclude from date-scoped loads
                # rather than guessing.
                return not (filters.date_from or filters.date_to)

            if filters.date_from and day < filters.date_from:
                return False
            if filters.date_to and day > filters.date_to:
                return False

        return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["AnalyticsLoader", "AnalyticsFilters", "AnalyticsSourceData"]

