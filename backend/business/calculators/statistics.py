"""VisionOps AI — Business Statistics Calculators.

Deterministic, pure statistical helpers used by the business layer for
operational KPI computation.

Numeric safety
--------------
Every public helper rejects:

* ``bool`` values (``bool`` is a subclass of ``int`` and is never a
  legitimate measurement),
* ``NaN`` and ``+/-Infinity``,
* non-numeric and malformed values (raises
  :class:`~backend.exceptions.ValidationError`),
* ``None`` where a number is required.

Empty inputs return the documented safe ``default`` instead of raising,
so business logic remains stable for empty analysis results.

NumPy scalar values (``numpy.float64``, ``numpy.int64``, ...) are
accepted and normalised to plain Python ``float`` / ``int`` in every
public result.

This module implements only the domain statistics required for business
KPI calculation; deep analytical aggregation belongs to
``backend.analytics``.
"""

from __future__ import annotations

import math
import numbers
import statistics as _stdlib_statistics
from collections.abc import Iterable
from typing import Any

from backend.exceptions import ValidationError

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "as_float",
    "as_int",
    "is_valid_number",
    "count",
    "sum_values",
    "mean",
    "median",
    "minimum",
    "maximum",
    "percentage",
    "rate",
    "clamp",
]


# ---------------------------------------------------------------------------
# Numeric coercion / validation
# ---------------------------------------------------------------------------


def is_valid_number(value: Any) -> bool:
    """Return ``True`` if *value* is a finite, non-bool numeric.

    Accepts Python ``int``/``float``, NumPy scalar numeric types, and
    numeric strings (for CSV-derived records). Rejects ``bool``,
    ``None``, ``NaN``, and ``+/-Infinity``.

    Args:
        value: The value to inspect.

    Returns:
        ``True`` if *value* is a legitimate finite number, else ``False``.
    """
    if isinstance(value, bool):
        return False
    try:
        parsed = _coerce_finite(value)
    except ValidationError:
        return False
    return parsed is not None


def as_float(value: Any, name: str = "value") -> float:
    """Coerce *value* into a finite Python ``float``.

    Accepts Python ``int``/``float``, NumPy scalar numeric types, and
    numeric strings. Rejects ``bool``, ``None``, ``NaN`` and
    ``+/-Infinity``.

    Args:
        value: The value to coerce.
        name: Optional field name used in error messages.

    Returns:
        A finite Python ``float``.

    Raises:
        ValidationError: If *value* is not a legitimate finite number.
    """
    parsed = _coerce_finite(value)
    if parsed is None:
        raise ValidationError(f"{name} must be a finite number, got {value!r}.")
    return parsed


def as_int(value: Any, name: str = "value") -> int:
    """Coerce *value* into a finite Python ``int``.

    The input must be numerically integral (no fractional part is
    silently dropped).

    Args:
        value: The value to coerce.
        name: Optional field name used in error messages.

    Returns:
        A Python ``int``.

    Raises:
        ValidationError: If *value* is not an integral finite number.
    """
    parsed = as_float(value, name=name)
    if not float(parsed).is_integer():
        raise ValidationError(f"{name} must be integral, got {value!r}.")
    return int(parsed)


def _coerce_finite(value: Any) -> float | None:
    """Return a finite ``float`` for a numeric-like value, else ``None``.

    Args:
        value: The value to coerce.

    Returns:
        A finite ``float``, or ``None`` when the value cannot be coerced.
    """
    if isinstance(value, bool):
        return None

    try:
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            parsed = float(stripped)
        elif isinstance(value, (int, float)) or isinstance(value, numbers.Real):
            parsed = float(value)
        else:
            return None
    except (TypeError, ValueError, OverflowError):
        return None

    if not math.isfinite(parsed):
        return None
    return parsed


# ---------------------------------------------------------------------------
# Descriptive statistics
# ---------------------------------------------------------------------------


def count(values: Iterable[Any]) -> int:
    """Return the number of valid finite numeric entries in *values*.

    Args:
        values: Iterable of candidate numeric values.

    Returns:
        Count of valid entries (>= 0).
    """
    return sum(1 for v in values if is_valid_number(v))


def sum_values(values: Iterable[Any], default: float = 0.0) -> float:
    """Return the sum of the valid numeric entries in *values*.

    Args:
        values: Iterable of numeric values.
        default: Value returned when there are no valid entries.

    Returns:
        Sum of valid finite numbers (Python ``float``).
    """
    return float(sum(as_float(v, name="sum_values item") for v in values)) or float(default)


def mean(values: Iterable[Any], default: float = 0.0) -> float:
    """Return the arithmetic mean of the valid numeric entries.

    Args:
        values: Iterable of numeric values.
        default: Value returned when there are no valid entries.

    Returns:
        Mean as a Python ``float``.

    Raises:
        ValidationError: If any entry is not a legitimate finite number.
    """
    items = list(values)
    if not items:
        return float(default)
    nums = [as_float(v, name="mean item") for v in items]
    return sum(nums) / len(nums)


def median(values: Iterable[Any], default: float = 0.0) -> float:
    """Return the median of the valid numeric entries.

    Args:
        values: Iterable of numeric values.
        default: Value returned when there are no valid entries.

    Returns:
        Median as a Python ``float``.

    Raises:
        ValidationError: If any entry is not a legitimate finite number.
    """
    items = list(values)
    if not items:
        return float(default)
    nums = [as_float(v, name="median item") for v in items]
    return float(_stdlib_statistics.median(nums))


def minimum(values: Iterable[Any], default: float | None = None) -> float | None:
    """Return the minimum of the valid numeric entries.

    Args:
        values: Iterable of numeric values.
        default: Value returned when there are no valid entries
            (``None`` if not provided).

    Returns:
        Minimum as a Python ``float``, or *default* for empty input.

    Raises:
        ValidationError: If any entry is not a legitimate finite number.
    """
    items = list(values)
    if not items:
        return default
    nums = [as_float(v, name="minimum item") for v in items]
    return float(min(nums))


def maximum(values: Iterable[Any], default: float | None = None) -> float | None:
    """Return the maximum of the valid numeric entries.

    Args:
        values: Iterable of numeric values.
        default: Value returned when there are no valid entries
            (``None`` if not provided).

    Returns:
        Maximum as a Python ``float``, or *default* for empty input.

    Raises:
        ValidationError: If any entry is not a legitimate finite number.
    """
    items = list(values)
    if not items:
        return default
    nums = [as_float(v, name="maximum item") for v in items]
    return float(max(nums))


# ---------------------------------------------------------------------------
# Rates / percentages
# ---------------------------------------------------------------------------


def percentage(value: Any, total: Any, default: float = 0.0) -> float:
    """Calculate *value* as a percentage of *total*.

    A zero (or non-positive) *total* returns *default* — it never
    raises for empty data.

    Args:
        value: The part value.
        total: The whole value.
        default: Value returned when *total* is zero.

    Returns:
        Percentage as a finite Python ``float``.
    """
    numerator = as_float(value, name="percentage value")
    denominator = as_float(total, name="percentage total")
    if denominator <= 0:
        return float(default)
    return float((numerator / denominator) * 100.0)


def rate(numerator: Any, denominator: Any, default: float = 0.0) -> float:
    """Safely divide *numerator* by *denominator*.

    A zero denominator returns *default* instead of raising.

    Args:
        numerator: The numerator.
        denominator: The denominator.
        default: Value returned when *denominator* is zero.

    Returns:
        Division result as a finite Python ``float``.
    """
    num = as_float(numerator, name="rate numerator")
    den = as_float(denominator, name="rate denominator")
    if den == 0:
        return float(default)
    return float(num / den)


def clamp(value: Any, low: float, high: float) -> float:
    """Clamp *value* into the inclusive range ``[low, high]``.

    Args:
        value: The value to clamp.
        low: Lower bound.
        high: Upper bound.

    Returns:
        The clamped finite Python ``float``.

    Raises:
        ValidationError: If the bounds are inverted or *value* is not
            finite.
    """
    if low > high:
        raise ValidationError(
            f"clamp lower bound ({low}) must not exceed upper bound ({high})."
        )
    parsed = as_float(value, name="clamp value")
    if parsed < low:
        return float(low)
    if parsed > high:
        return float(high)
    return parsed

