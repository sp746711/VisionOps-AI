"""VisionOps AI — Analytics Data Cleaning.

This module implements the analytics data-cleaning layer.  It cleans raw
analytics source records into normalised, analytics-compatible records:

* missing-value handling (configurable presence policy),
* whitespace normalization on string fields,
* numeric coercion with strict **NaN / ±Infinity / bool** rejection,
* datetime normalization to timezone-aware UTC,
* duplicate removal (stable first-seen order),
* malformed-row filtering,
* confidence validation against ``[0.0, 1.0]``,
* class-name and severity normalization,
* rejected-row reporting via :class:`CleaningResult`.

Design rules:

* Invalid records are **dropped**, not silently turned into
  valid-looking data.
* Rejected rows are reported through a :class:`CleaningResult` summary
  (counts are always reported; per-row diagnostics are DEBUG).
* Cleaning is deterministic: for the same input, the same output order is
  produced regardless of execution order.
* ``bool`` is rejected wherever a genuine number is required because
  ``bool`` is a subclass of ``int`` in Python.
* NumPy scalar values (``np.float32/64``, ``np.int32/64``) are normalised
  to plain Python ``int``/``float`` before public results are returned.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable

from backend.exceptions import AnalyticsError, ValidationError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_CONFIDENCE: float = 0.0
_MAX_CONFIDENCE: float = 1.0

_VALID_SEVERITIES: frozenset[str] = frozenset(
    {"low", "medium", "high", "critical"}
)

_VALID_CLASS_ALIASES: dict[str, str] = {
    "person": "person",
    "people": "person",
    "forklift": "forklift",
    "forklifts": "forklift",
    "pallet": "pallet",
    "pallets": "pallet",
    "truck": "truck",
    "trucks": "truck",
    "dock": "dock",
    "docks": "dock",
    "product": "product",
    "products": "product",
    "spoiled_food": "spoiled_food",
    "spoiled food": "spoiled_food",
}


# ---------------------------------------------------------------------------
# Public data containers
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CleaningResult:
    """Outcome of a cleaning run over a record collection.

    Attributes:
        cleaned: Cleaned, deterministic record list.
        total_input: Number of records supplied.
        accepted: Number of records kept.
        rejected: Number of records dropped.
        rejected_reasons: Mapping from reason label to count.
    """

    cleaned: list[dict[str, Any]] = field(default_factory=list)
    total_input: int = 0
    accepted: int = 0
    rejected: int = 0
    rejected_reasons: dict[str, int] = field(default_factory=dict)

    @property
    def rejection_rate(self) -> float:
        """Return the proportion of rejected records (0.0–1.0)."""
        if self.total_input == 0:
            return 0.0
        return self.rejected / self.total_input

    def _record_rejection(self, reason: str) -> None:
        """Increment the counter for a rejection reason."""
        self.rejected += 1
        self.rejected_reasons[reason] = self.rejected_reasons.get(reason, 0) + 1


# ---------------------------------------------------------------------------
# DataCleaner
# ---------------------------------------------------------------------------


class DataCleaner:
    """Cleans raw analytics records into normalised analytical records.

    Args:
        require_ids: When ``True`` (default), records missing their
            identifier column are rejected.
        drop_duplicates: When ``True`` (default), duplicate records are
            removed keeping the first occurrence.
        validate_confidence: When ``True`` (default), detection
            confidence values are validated against ``[0.0, 1.0]``.
        strip_whitespace: When ``True`` (default), string fields are
            whitespace-stripped.
    """

    def __init__(
        self,
        *,
        require_ids: bool = True,
        drop_duplicates: bool = True,
        validate_confidence: bool = True,
        strip_whitespace: bool = True,
    ) -> None:
        """Initialise the data cleaner."""
        self._require_ids = require_ids
        self._drop_duplicates = drop_duplicates
        self._validate_confidence = validate_confidence
        self._strip_whitespace = strip_whitespace

    # ------------------------------------------------------------------
    # Top-level cleaning helpers
    # ------------------------------------------------------------------

    def clean_detections(
        self,
        records: Iterable[dict[str, Any]],
    ) -> CleaningResult:
        """Clean detection records.

        Args:
            records: Raw detection records (usually from the storage
                layer).

        Returns:
            A :class:`CleaningResult` with cleaned detection records.
        """
        return self._clean_records(
            records,
            id_keys=("detection_id", "detectionId"),
            numeric_keys=("confidence", "bbox_x", "bbox_y", "bbox_w", "bbox_h"),
            string_keys=("class_name", "video_id", "track_id"),
            datetime_keys=("created_at",),
            confidence_keys=("confidence",),
            class_keys=("class_name",),
        )

    def clean_events(
        self,
        records: Iterable[dict[str, Any]],
    ) -> CleaningResult:
        """Clean business-event records.

        Args:
            records: Raw event records.

        Returns:
            A :class:`CleaningResult` with cleaned event records.
        """
        return self._clean_records(
            records,
            id_keys=("event_id", "eventId"),
            string_keys=("event_type", "video_id", "description", "source"),
            datetime_keys=("created_at", "updated_at"),
            severity_keys=("severity",),
        )

    def clean_alerts(
        self,
        records: Iterable[dict[str, Any]],
    ) -> CleaningResult:
        """Clean alert records.

        Args:
            records: Raw alert records.

        Returns:
            A :class:`CleaningResult` with cleaned alert records.
        """
        return self._clean_records(
            records,
            id_keys=("alert_id", "alertId"),
            string_keys=("video_id", "message", "source"),
            datetime_keys=(
                "created_at",
                "updated_at",
                "acknowledged_at",
            ),
            boolean_keys=("acknowledged", "escalated"),
            severity_keys=("severity",),
        )

    def clean_kpis(
        self,
        records: Iterable[dict[str, Any]],
    ) -> CleaningResult:
        """Clean KPI records.

        Args:
            records: Raw KPI records.

        Returns:
            A :class:`CleaningResult` with cleaned KPI records.
        """
        return self._clean_records(
            records,
            id_keys=("kpi_id", "kpiId"),
            string_keys=("metric", "video_id", "unit"),
            numeric_keys=("value",),
            datetime_keys=("timestamp",),
        )

    def clean_analytics(
        self,
        records: Iterable[dict[str, Any]],
    ) -> CleaningResult:
        """Clean aggregated-analytics records.

        Args:
            records: Raw analytics records.

        Returns:
            A :class:`CleaningResult` with cleaned analytics records.
        """
        return self._clean_records(
            records,
            id_keys=("analytics_id", "analyticsId"),
            string_keys=("metric", "video_id", "unit"),
            numeric_keys=("value",),
            datetime_keys=("created_at", "period_start", "period_end"),
        )

    def clean_videos(
        self,
        records: Iterable[dict[str, Any]],
    ) -> CleaningResult:
        """Clean video metadata records.

        Args:
            records: Raw video metadata records.

        Returns:
            A :class:`CleaningResult` with cleaned video records.
        """
        return self._clean_records(
            records,
            id_keys=("video_id", "videoId"),
            string_keys=("filename", "status", "content_type", "error_message"),
            numeric_keys=(
                "file_size",
                "duration_seconds",
                "total_frames",
                "fps",
            ),
            datetime_keys=(
                "created_at",
                "updated_at",
                "processing_started_at",
                "processing_completed_at",
            ),
        )

    def clean_all(
        self,
        data: dict[str, Any],
    ) -> dict[str, CleaningResult]:
        """Clean every store in a source-data mapping.

        Args:
            data: Mapping keyed by store name to record collections.
                Valid keys: ``videos``, ``detections``, ``events``,
                ``alerts``, ``kpis``, ``analytics``.

        Returns:
            Mapping from store name to its :class:`CleaningResult`.
        """
        cleanable: dict[str, Callable[[Iterable[dict[str, Any]]], CleaningResult]] = {
            "videos": self.clean_videos,
            "detections": self.clean_detections,
            "events": self.clean_events,
            "alerts": self.clean_alerts,
            "kpis": self.clean_kpis,
            "analytics": self.clean_analytics,
        }

        results: dict[str, CleaningResult] = {}
        for store_name, cleaner_fn in cleanable.items():
            records = data.get(store_name)
            results[store_name] = (
                cleaner_fn(records) if records is not None else CleaningResult()
            )
            logger.info(
                "Cleaning '%s': %d accepted, %d rejected.",
                store_name,
                results[store_name].accepted,
                results[store_name].rejected,
            )
        return results

    # ------------------------------------------------------------------
    # Core cleaning engine
    # ------------------------------------------------------------------

    def _clean_records(
        self,
        records: Iterable[dict[str, Any]],
        *,
        id_keys: tuple[str, ...],
        numeric_keys: tuple[str, ...] = (),
        string_keys: tuple[str, ...] = (),
        datetime_keys: tuple[str, ...] = (),
        boolean_keys: tuple[str, ...] = (),
        confidence_keys: tuple[str, ...] = (),
        class_keys: tuple[str, ...] = (),
        severity_keys: tuple[str, ...] = (),
    ) -> CleaningResult:
        """Clean a generic record collection.

        Args:
            records: Raw record collection.
            id_keys: Candidate identifier column names.
            numeric_keys: Column names expected to hold numbers.
            string_keys: Column names expected to hold strings.
            datetime_keys: Column names expected to hold datetimes.
            boolean_keys: Column names expected to hold booleans.
            confidence_keys: Column names whose values must be
                confidence scores in ``[0.0, 1.0]``.
            class_keys: Column names whose values are class names
                (normalised through known aliases).
            severity_keys: Column names whose values are severities.

        Returns:
            A :class:`CleaningResult`.
        """
        result = CleaningResult()
        seen_ids: set[object] = set()

        for raw in records:
            if not isinstance(raw, dict):
                result._record_rejection("not_a_dict")
                continue

            try:
                cleaned = self._clean_record(
                    raw,
                    id_keys=id_keys,
                    numeric_keys=numeric_keys,
                    string_keys=string_keys,
                    datetime_keys=datetime_keys,
                    boolean_keys=boolean_keys,
                    confidence_keys=confidence_keys,
                    class_keys=class_keys,
                    severity_keys=severity_keys,
                )
            except ValidationError as exc:
                result._record_rejection(exc.message)
                logger.debug("Rejected record %s: %s", raw.get(next(iter(id_keys), ""), "?"), exc)
                continue

            # Duplicate detection by ID (first-seen wins).
            if self._drop_duplicates and id_keys:
                id_value = cleaned.get(next(iter(id_keys)))
                if id_value in seen_ids:
                    result._record_rejection("duplicate")
                    logger.debug(
                        "Rejected duplicate record with id=%s.", id_value
                    )
                    continue
                seen_ids.add(id_value)

            result.cleaned.append(cleaned)

        result.total_input = sum(
            1 for _ in records
        ) if isinstance(records, Iterable) else 0

        # ``total_input`` consumed the generator if it is one.  Recompute
        # from accepted+rejected if we consumed a non-repeatable source.
        if result.total_input == 0 and (result.accepted or result.rejected):
            result.total_input = result.accepted + result.rejected

        result.accepted = len(result.cleaned)
        if result.rejected == 0:
            result.total_input = result.accepted

        return result

    def _clean_record(
        self,
        raw: dict[str, Any],
        *,
        id_keys: tuple[str, ...],
        numeric_keys: tuple[str, ...],
        string_keys: tuple[str, ...],
        datetime_keys: tuple[str, ...],
        boolean_keys: tuple[str, ...],
        confidence_keys: tuple[str, ...],
        class_keys: tuple[str, ...],
        severity_keys: tuple[str, ...],
    ) -> dict[str, Any]:
        """Clean a single raw record dictionary.

        Args:
            raw: Raw record.
            id_keys: Candidate identifier column names.
            numeric_keys: Numeric column names.
            string_keys: String column names.
            datetime_keys: Datetime column names.
            boolean_keys: Boolean column names.
            confidence_keys: Confidence column names.
            class_keys: Class-name column names.
            severity_keys: Severity column names.

        Returns:
            A cleaned record dictionary.

        Raises:
            ValidationError: If a required ID is missing or a value is
                not cleanable.
        """
        cleaned: dict[str, Any] = {}

        # Text normalization first so later lookups are reliable.
        normalized: dict[str, Any] = {}
        for key, value in raw.items():
            if self._strip_whitespace and isinstance(value, str):
                normalized[key] = value.strip()
            else:
                normalized[key] = value

        # Required ID
        if self._require_ids:
            id_value = self._first_present(normalized, id_keys)
            if id_value is None or not str(id_value).strip():
                raise ValidationError("missing_required_id")
            cleaned[next(iter(id_keys))] = str(id_value).strip()

        # Strings
        for key in string_keys:
            value = normalized.get(key)
            if value is not None:
                cleaned[key] = str(value).strip()

        # Numeric columns (strict: reject NaN/Inf/bool)
        for key in numeric_keys:
            if key in normalized and normalized[key] is not None:
                cleaned[key] = self._to_finite_number(
                    normalized[key], field=key
                )

        # Datetime columns
        for key in datetime_keys:
            if key in normalized and normalized[key] is not None:
                cleaned[key] = self._to_utc_datetime(normalized[key], field=key)

        # Booleans
        for key in boolean_keys:
            if key in normalized and normalized[key] is not None:
                cleaned[key] = self._to_boolean(normalized[key], field=key)

        # Confidence columns
        if self._validate_confidence:
            for key in confidence_keys:
                if key in normalized and normalized[key] is not None:
                    confidence = self._to_finite_number(
                        normalized[key], field=key
                    )
                    if not (_MIN_CONFIDENCE <= confidence <= _MAX_CONFIDENCE):
                        raise ValidationError(f"confidence_out_of_range:{key}")
                    cleaned[key] = confidence

        # Class-name normalization
        for key in class_keys:
            if key in normalized and normalized[key] is not None:
                cleaned[key] = self._normalize_class(normalized[key], field=key)

        # Severity normalization
        for key in severity_keys:
            if key in normalized and normalized[key] is not None:
                cleaned[key] = self._normalize_severity(normalized[key], field=key)

        # Preserve any remaining unknown columns as-is (stripped).
        for key, value in normalized.items():
            if key not in cleaned:
                cleaned[key] = value

        return cleaned

    # ------------------------------------------------------------------
    # Generic list helpers
    # ------------------------------------------------------------------

    def _clean_records_list(
        self,
        records: Iterable[dict[str, Any] | None],
        id_key: str,
        numeric_keys: tuple[str, ...],
        string_keys: tuple[str, ...],
        datetime_keys: tuple[str, ...],
        severity_keys: tuple[str, ...] = (),
        class_keys: tuple[str, ...] = (),
        confidence_keys: tuple[str, ...] = (),
    ) -> CleaningResult:
        """Alias for :meth:`_clean_records` with a single ID key."""
        return self._clean_records(
            (r for r in records if r is not None),
            id_keys=(id_key,),
            numeric_keys=numeric_keys,
            string_keys=string_keys,
            datetime_keys=datetime_keys,
            severity_keys=severity_keys,
            class_keys=class_keys,
            confidence_keys=confidence_keys,
        )

    # ------------------------------------------------------------------
    # Value coercion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _first_present(
        data: dict[str, Any],
        keys: tuple[str, ...],
    ) -> Any:
        """Return the first non-``None`` value for any of *keys*."""
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]
        return None

    @staticmethod
    def _to_finite_number(value: Any, *, field: str) -> int | float:
        """Coerce *value* to a finite Python number.

        NumPy scalar types are normalised to plain ``int``/``float``.
        ``bool``, ``nan``, ``+Inf`` and ``-Inf`` are rejected.

        Args:
            value: Raw value.
            field: Field name used in error messages.

        Returns:
            A plain Python ``int`` or ``float``.

        Raises:
            ValidationError: If *value* is a bool or cannot be coerced to
                a finite number.
        """
        # Normalise supported NumPy scalars (only if NumPy is available).
        if _HAS_NUMPY:
            try:
                import numpy as _np  # type: ignore

                if isinstance(value, (_np.bool_)):
                    raise ValidationError(
                        f"field '{field}' must be a number, got bool."
                    )
                if isinstance(value, (_np.integer, _np.floating)):
                    value = value.item()
            except ImportError:  # pragma: no cover - NumPy absent
                pass

        if isinstance(value, bool):
            raise ValidationError(
                f"field '{field}' must be a number, got bool."
            )

        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                f"field '{field}' is not numeric: {value!r}."
            ) from exc

        if not math.isfinite(number):
            raise ValidationError(
                f"field '{field}' must be finite (rejected NaN/Infinity): "
                f"{value!r}."
            )

        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, str) and _is_integer_string(value):
            return int(value)
        return number

    @staticmethod
    def _to_utc_datetime(value: Any, *, field: str) -> datetime:
        """Normalise *value* to a timezone-aware UTC datetime.

        Args:
            value: ``datetime`` or ISO-8601 string.
            field: Field name used in error messages.

        Returns:
            Timezone-aware UTC datetime.

        Raises:
            ValidationError: If *value* is malformed.
        """
        parsed: datetime
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValidationError(
                    f"Invalid ISO-8601 timestamp for '{field}': {value!r}."
                ) from exc
        else:
            raise ValidationError(
                f"Timestamp '{field}' must be a datetime or string, got "
                f"{type(value).__name__}."
            )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=_UTC)
        return parsed.astimezone(_UTC)

    @staticmethod
    def _to_boolean(value: Any, *, field: str) -> bool:
        """Coerce common truthy/falsy representations to a bool.

        Args:
            value: Raw boolean-like value.
            field: Field name used in error messages.

        Returns:
            A plain Python ``bool``.

        Raises:
            ValidationError: If *value* cannot be interpreted as a bool.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return value != 0
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in ("true", "yes", "1", "y"):
                return True
            if lowered in ("false", "no", "0", "n"):
                return False
        raise ValidationError(
            f"field '{field}' is not a boolean: {value!r}."
        )

    @staticmethod
    def _normalize_class(value: Any, *, field: str) -> str:
        """Normalise a class-name value through known aliases.

        Args:
            value: Raw class name.
            field: Field name used in error messages.

        Returns:
            Normalised class name.

        Raises:
            ValidationError: If *value* is not a string.
        """
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(
                f"field '{field}' must be a non-empty string."
            )
        normalized = value.strip().lower()
        return _VALID_CLASS_ALIASES.get(normalized, normalized)

    @staticmethod
    def _normalize_severity(value: Any, *, field: str) -> str:
        """Normalise a severity value.

        Args:
            value: Raw severity.
            field: Field name used in error messages.

        Returns:
            Lowercased severity string.

        Raises:
            ValidationError: If *value* is not a known severity.
        """
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(
                f"field '{field}' must be a non-empty string."
            )
        normalized = value.strip().lower()
        if normalized not in _VALID_SEVERITIES:
            raise ValidationError(
                f"field '{field}' has invalid severity '{value}'. "
                f"Valid: {', '.join(sorted(_VALID_SEVERITIES))}."
            )
        return normalized


# ---------------------------------------------------------------------------
# Module-level helpers / constants
# ---------------------------------------------------------------------------

from datetime import timezone as _timezone_module

_UTC = _timezone_module.utc

#: Lazily detected whether NumPy is importable.
_HAS_NUMPY: bool = True
try:  # pragma: no cover - environment dependent
    import numpy as _numpy  # noqa: F401

    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False


def _is_integer_string(value: str) -> bool:
    """Return whether *value* is a string containing an integer."""
    try:
        int(value)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["DataCleaner", "CleaningResult"]

