"""VisionOps AI — Date/Time Utilities.

Reusable helpers for UTC/local timestamps, ISO formatting, duration
formatting, and timezone conversions. Shared across the entire backend.

Usage:
    from backend.utils.date_utils import now_utc, format_duration, ...
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta, tzinfo
from typing import Literal

logger = logging.getLogger("visionops.utils.date_utils")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_UNITS: dict[str, int] = {
    "s": 1,
    "ms": 1_000,
    "us": 1_000_000,
}

_DURATION_PARTS: list[tuple[str, int]] = [
    ("d", 86_400),
    ("h", 3_600),
    ("m", 60),
    ("s", 1),
]


# ---------------------------------------------------------------------------
# Current Time
# ---------------------------------------------------------------------------


def now_utc() -> datetime:
    """Return the current UTC datetime with timezone awareness.

    Returns:
        A timezone-aware :class:`datetime.datetime` in UTC.

    Example:
        >>> now_utc()
        datetime(2025, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
    """
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    """Return the current local datetime with timezone awareness.

    Uses the system's local timezone.

    Returns:
        A timezone-aware :class:`datetime.datetime` in the local timezone.

    Example:
        >>> now_local()
        datetime(2025, 1, 15, 7, 30, 0, tzinfo=...)
    """
    return datetime.now().astimezone()


# ---------------------------------------------------------------------------
# Timestamp Conversion
# ---------------------------------------------------------------------------


def timestamp_to_datetime(
    ts: float,
    unit: Literal["s", "ms", "us"] = "s",
    tz: tzinfo | None = None,
) -> datetime:
    """Convert a Unix timestamp to a timezone-aware datetime.

    Args:
        ts: Timestamp value.
        unit: Unit of the timestamp — ``"s"`` (seconds, default),
            ``"ms"`` (milliseconds), or ``"us"`` (microseconds).
        tz: Target timezone. If ``None``, defaults to UTC.

    Returns:
        Timezone-aware :class:`datetime.datetime`.

    Raises:
        ValueError: If *unit* is invalid.

    Example:
        >>> timestamp_to_datetime(1736933400)
        datetime(2025, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
    """
    if unit not in _UNITS:
        raise ValueError(f"Unsupported timestamp unit: {unit!r}. Use 's', 'ms', or 'us'.")

    divisor = _UNITS[unit]
    return datetime.fromtimestamp(ts / divisor, tz=tz or timezone.utc)


def datetime_to_timestamp(
    dt: datetime,
    unit: Literal["s", "ms", "us"] = "s",
) -> float:
    """Convert a datetime to a Unix timestamp.

    Args:
        dt: The datetime to convert (timezone-naive is treated as UTC).
        unit: Desired unit — ``"s"`` (seconds, default), ``"ms"``
            (milliseconds), or ``"us"`` (microseconds).

    Returns:
        Timestamp as a float.

    Raises:
        ValueError: If *unit* is invalid.

    Example:
        >>> from datetime import datetime, timezone
        >>> dt = datetime(2025, 1, 15, tzinfo=timezone.utc)
        >>> datetime_to_timestamp(dt)
        1736899200.0
    """
    if unit not in _UNITS:
        raise ValueError(f"Unsupported timestamp unit: {unit!r}. Use 's', 'ms', or 'us'.")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    multiplier = _UNITS[unit]
    return dt.timestamp() * multiplier


# ---------------------------------------------------------------------------
# ISO Formatting
# ---------------------------------------------------------------------------


def format_iso(
    dt: datetime | None = None,
    sep: str = "T",
    timespec: Literal["auto", "hours", "minutes", "seconds", "milliseconds", "microseconds"] = "seconds",
) -> str:
    """Format a datetime as an ISO 8601 string.

    Args:
        dt: Datetime to format. If ``None``, uses current UTC time.
        sep: Separator between date and time (default: ``"T"``).
        timespec: Precision of time component (default: ``"seconds"``).

    Returns:
        ISO 8601 formatted string.

    Example:
        >>> format_iso(timespec="seconds")
        '2025-01-15T12:30:00+00:00'
    """
    if dt is None:
        dt = now_utc()
    return dt.isoformat(sep=sep, timespec=timespec)


# ---------------------------------------------------------------------------
# Duration Formatting
# ---------------------------------------------------------------------------


def format_duration(
    seconds: float,
    granularity: int = 2,
) -> str:
    """Format a duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds.
        granularity: Number of non-zero components to show (default: 2).

    Returns:
        Human-readable string, e.g. ``"1d 2h 30m 15s"``.

    Examples:
        >>> format_duration(90061)
        '1d 1h 1m 1s'
        >>> format_duration(3661, granularity=2)
        '1h 1m'
        >>> format_duration(0)
        '0s'
    """
    remaining = int(seconds)
    parts: list[str] = []

    for label, count in _DURATION_PARTS:
        if remaining >= count or (label == "s" and not parts):
            value, remaining = divmod(remaining, count)
            parts.append(f"{value}{label}")

    shown = parts[:granularity] if granularity > 0 else parts
    return " ".join(shown) if shown else "0s"


# ---------------------------------------------------------------------------
# Time Difference
# ---------------------------------------------------------------------------


def time_difference(
    start: datetime,
    end: datetime | None = None,
    unit: Literal["s", "ms", "us"] = "s",
) -> float:
    """Calculate the difference between two datetimes in the specified unit.

    Args:
        start: Start datetime.
        end: End datetime. If ``None``, uses current UTC time.
        unit: Unit for the result — ``"s"`` (default), ``"ms"``, or
            ``"us"``.

    Returns:
        Difference in the requested unit.

    Raises:
        ValueError: If *unit* is invalid.

    Example:
        >>> time_difference(
        ...     datetime(2025, 1, 1, tzinfo=timezone.utc),
        ...     datetime(2025, 1, 2, tzinfo=timezone.utc),
        ... )
        86400.0
    """
    if unit not in _UNITS:
        raise ValueError(f"Unsupported unit: {unit!r}. Use 's', 'ms', or 'us'.")

    end_dt = end or now_utc()
    diff = end_dt - start
    return diff.total_seconds() * (1 if unit == "s" else _UNITS[unit])


# ---------------------------------------------------------------------------
# Timezone Conversion
# ---------------------------------------------------------------------------


def utc_to_local(dt: datetime) -> datetime:
    """Convert a UTC datetime to the system's local timezone.

    Args:
        dt: UTC datetime (naive treated as UTC).

    Returns:
        Local timezone-aware datetime.

    Example:
        >>> utc_to_local(datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc))
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone()


def local_to_utc(dt: datetime) -> datetime:
    """Convert a local datetime to UTC.

    Args:
        dt: Local datetime (naive treated as local time).

    Returns:
        UTC timezone-aware datetime.

    Example:
        >>> local_to_utc(datetime(2025, 1, 15, 7, 0))
    """
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.astimezone(timezone.utc)
