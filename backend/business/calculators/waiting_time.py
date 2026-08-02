"""VisionOps AI — Waiting Time Calculator.

Deterministic, pure calculations for waiting durations (e.g. a truck
waiting in queue before dock assignment).

Waiting time is only computed from **real timestamps**.  The following
edge cases are handled explicitly:

* no observations            -> empty summary / zero values
* one observation            -> that single value is used
* missing timestamps         -> record excluded
* invalid ordering           -> duration clamped to ``0.0``
  (never negative — there is no meaningful negative wait)
* zero-duration cases        -> ``0.0``

A reversed interval for waiting data is treated as "no waiting occurred"
rather than an error, because a negative waiting time is not a valid
operational fact.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from typing import Any

from backend.business.calculators.statistics import as_float, maximum, mean, minimum

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "waiting_duration",
    "average_waiting_time",
    "waiting_time_summary",
    "waiting_durations_from_records",
]


# ---------------------------------------------------------------------------
# Duration calculations
# ---------------------------------------------------------------------------


def _coerce_utc(value: datetime | str, name: str) -> datetime | None:
    """Normalise a timestamp to tz-aware UTC, or return ``None``.

    Args:
        value: A datetime-like value.
        name: Field name used for error context (unused on failure).

    Returns:
        A timezone-aware UTC ``datetime``, or ``None`` when the value is
        missing or malformed.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def waiting_duration(
    start: datetime | str | None,
    end: datetime | str | None,
) -> float | None:
    """Return the waiting duration (seconds) between *start* and *end*.

    Returns ``None`` when either timestamp is missing/unsupported
    (no synthetic value is invented).  A reversed interval is clamped to
    ``0.0`` so waiting time is never negative.

    Args:
        start: Waiting-period start timestamp.
        end: Waiting-period end timestamp.

    Returns:
        Non-negative duration in seconds, or ``None`` if the timestamps
        are not usable.
    """
    start_dt = _coerce_utc(start, "start")
    end_dt = _coerce_utc(end, "end")
    if start_dt is None or end_dt is None:
        return None
    diff = (end_dt - start_dt).total_seconds()
    return float(max(diff, 0.0))


def average_waiting_time(
    durations: Iterable[float | int],
    default: float = 0.0,
) -> float:
    """Return the mean waiting duration (seconds) of *durations*.

    Args:
        durations: Iterable of duration values in seconds.
        default: Value returned for empty input.

    Returns:
        Average waiting duration in seconds.
    """
    items = [as_float(d, name="waiting duration") for d in durations]
    return mean(items, default=float(default))


def waiting_time_summary(durations: Iterable[float | int]) -> dict[str, float]:
    """Build a deterministic summary of waiting durations.

    Args:
        durations: Iterable of duration values in seconds.

    Returns:
        Dictionary with ``count``, ``total_seconds``, ``average_seconds``,
        ``min_seconds`` and ``max_seconds``.
    """
    items = [as_float(d, name="waiting duration") for d in durations]
    return {
        "count": len(items),
        "total_seconds": float(sum(items)),
        "average_seconds": float(mean(items, default=0.0)),
        "min_seconds": float(minimum(items, default=0.0) or 0.0),
        "max_seconds": float(maximum(items, default=0.0) or 0.0),
    }


def waiting_durations_from_records(
    records: Iterable[Mapping[str, Any]],
    start_key: str,
    end_key: str,
) -> dict[str, Any]:
    """Compute waiting durations from timestamped record mappings.

    Records missing either timestamp are skipped.  Reversed intervals
    contribute ``0.0`` (no negative waiting time).

    Args:
        records: Iterable of record mappings containing timestamps.
        start_key: Key for the start timestamp.
        end_key: Key for the end timestamp.

    Returns:
        A :func:`waiting_time_summary` dictionary plus ``valid_count``
        and ``skipped_count``.
    """
    durations: list[float] = []
    skipped = 0
    for record in records:
        start = record.get(start_key)
        end = record.get(end_key)
        if not start or not end:
            skipped += 1
            continue
        duration = waiting_duration(start, end)
        if duration is None:
            skipped += 1
        else:
            durations.append(duration)

    summary = waiting_time_summary(durations)
    summary["valid_count"] = summary.pop("count")
    summary["skipped_count"] = skipped
    return summary

