"""VisionOps AI — Loading Time Calculator.

Deterministic, pure calculations for loading / unloading durations.

Durations are always derived from **real timestamps** (UTC-aware
datetimes).  No synthetic timestamps are ever invented.  Invalid
ordering (``end < start``) raises
:class:`~backend.exceptions.ValidationError` because a reversed interval
is malformed input — a loading operation cannot finish before it starts.

Results are expressed explicitly in seconds (the canonical unit); a
convenience ``to_minutes`` converter avoids silent unit mixing.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from backend.exceptions import ValidationError
from backend.business.calculators.statistics import (
    as_float,
    maximum,
    mean,
    minimum,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "duration_between",
    "to_minutes",
    "average_loading_time",
    "total_loading_time",
    "loading_time_summary",
    "duration_from_records",
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _coerce_utc(value: datetime | str, name: str) -> datetime:
    """Normalise a datetime-like value to timezone-aware UTC.

    Args:
        value: A tz-aware/naive ``datetime`` or an ISO-8601 string.
        name: Field name used in error messages.

    Returns:
        A timezone-aware UTC ``datetime``.

    Raises:
        ValidationError: If *value* is not a valid timestamp.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValidationError(
                f"{name} is not a valid ISO-8601 timestamp: {value!r}."
            ) from exc
    else:
        raise ValidationError(
            f"{name} must be a datetime or ISO-8601 string, got "
            f"{type(value).__name__}."
        )

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Duration calculations
# ---------------------------------------------------------------------------


def duration_between(start: datetime | str, end: datetime | str) -> float:
    """Return the duration (seconds) between *start* and *end*.

    Durations are computed from real timestamps only.

    Args:
        start: Loading-operation start timestamp.
        end: Loading-operation end timestamp.

    Returns:
        Non-negative duration in seconds (Python ``float``).

    Raises:
        ValidationError: If either timestamp is missing/malformed, or if
            *end* is earlier than *start* (invalid ordering).
    """
    start_dt = _coerce_utc(start, "start")
    end_dt = _coerce_utc(end, "end")
    if end_dt < start_dt:
        raise ValidationError(
            "Loading duration end must not be earlier than start "
            f"({start_dt.isoformat()} > {end_dt.isoformat()})."
        )
    return float((end_dt - start_dt).total_seconds())


def to_minutes(seconds: float | int) -> float:
    """Convert a seconds duration to minutes.

    Args:
        seconds: Duration in seconds (finite, non-negative).

    Returns:
        Duration in minutes as a Python ``float``.
    """
    value = as_float(seconds, name="seconds")
    if value < 0:
        raise ValidationError("seconds must be non-negative.")
    return value / 60.0


def average_loading_time(durations: Iterable[float | int], default: float = 0.0) -> float:
    """Return the mean loading duration (seconds) of *durations*.

    Args:
        durations: Iterable of duration values in seconds.
        default: Value returned for empty input.

    Returns:
        Average duration in seconds.

    Raises:
        ValidationError: If any duration is not a finite non-negative
            number.
    """
    items = [as_float(d, name="loading duration") for d in durations]
    if any(d < 0 for d in items):
        raise ValidationError("Loading durations must be non-negative.")
    return mean(items, default=float(default))


def total_loading_time(durations: Iterable[float | int], default: float = 0.0) -> float:
    """Return the total loading duration (seconds) of *durations*.

    Args:
        durations: Iterable of duration values in seconds.
        default: Value returned for empty input.

    Returns:
        Total duration in seconds.
    """
    items = [as_float(d, name="loading duration") for d in durations]
    if any(d < 0 for d in items):
        raise ValidationError("Loading durations must be non-negative.")
    return float(sum(items)) if items else float(default)


def loading_time_summary(
    durations: Iterable[float | int],
) -> dict[str, float]:
    """Build a deterministic summary of loading durations.

    Args:
        durations: Iterable of duration values in seconds.

    Returns:
        Dictionary with ``count``, ``total_seconds``, ``average_seconds``,
        ``min_seconds`` and ``max_seconds`` (all Python ``float``/``int``).
        Empty input yields a summary with count ``0`` and zero durations.
    """
    items = [as_float(d, name="loading duration") for d in durations]
    if any(d < 0 for d in items):
        raise ValidationError("Loading durations must be non-negative.")

    return {
        "count": len(items),
        "total_seconds": float(sum(items)),
        "average_seconds": float(mean(items, default=0.0)),
        "min_seconds": float(minimum(items, default=0.0) or 0.0),
        "max_seconds": float(maximum(items, default=0.0) or 0.0),
    }


def duration_from_records(
    records: Iterable[Mapping[str, Any]],
    start_key: str,
    end_key: str,
) -> dict[str, Any]:
    """Compute loading durations from timestamped record mappings.

    Only records that contain both *start_key* and *end_key* as valid
    timestamps are used.  Records with invalid ordering are excluded
    (they cannot represent a real loading interval) — no synthetic value
    is produced for them.

    Args:
        records: Iterable of record mappings containing timestamps.
        start_key: Key for the start timestamp in each record.
        end_key: Key for the end timestamp in each record.

    Returns:
        A :func:`loading_time_summary` dictionary plus ``valid_count``
        and ``skipped_count`` reflecting how many records were usable.
    """
    durations: list[float] = []
    skipped = 0
    for record in records:
        start = record.get(start_key)
        end = record.get(end_key)
        if not start or not end:
            skipped += 1
            continue
        try:
            durations.append(duration_between(start, end))
        except ValidationError:
            skipped += 1

    summary = loading_time_summary(durations)
    summary["valid_count"] = summary.pop("count")
    summary["skipped_count"] = skipped
    return summary

