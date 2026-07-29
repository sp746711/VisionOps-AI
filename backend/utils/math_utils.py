"""VisionOps AI — Math Utilities.

Reusable generic mathematical helpers: clamping, percentage, average,
min/max, distance, normalization, safe division, rounding, median,
variance, and standard deviation. No AI model logic included.

Usage:
    from backend.utils.math_utils import clamp, safe_division, median, ...
"""

from __future__ import annotations

import logging
import math
import statistics
from collections.abc import Sequence

logger = logging.getLogger("visionops.utils.math_utils")


# ---------------------------------------------------------------------------
# Clamp
# ---------------------------------------------------------------------------


def clamp(
    value: float | int,
    min_val: float | int,
    max_val: float | int,
) -> float | int:
    """Clamp *value* to the range [*min_val*, *max_val*].

    Args:
        value: The value to clamp.
        min_val: Minimum bound.
        max_val: Maximum bound.

    Returns:
        The clamped value.

    Raises:
        ValueError: If *min_val* > *max_val*.

    Example:
        >>> clamp(15, 0, 10)
        10
    """
    if min_val > max_val:
        raise ValueError(f"min_val ({min_val}) > max_val ({max_val})")
    if value < min_val:
        return min_val
    if value > max_val:
        return max_val
    return value


# ---------------------------------------------------------------------------
# Percentage
# ---------------------------------------------------------------------------


def percentage(
    value: float | int,
    total: float | int,
    decimals: int = 2,
) -> float:
    """Calculate the percentage of *value* relative to *total*.

    Args:
        value: The part value.
        total: The whole value.
        decimals: Decimal places to round to (default: 2).

    Returns:
        Percentage as a float.

    Raises:
        ZeroDivisionError: If *total* is zero.

    Example:
        >>> percentage(25, 200)
        12.5
    """
    if total == 0:
        raise ZeroDivisionError("Cannot calculate percentage: total is zero")
    return round((float(value) / float(total)) * 100.0, decimals)


# ---------------------------------------------------------------------------
# Average
# ---------------------------------------------------------------------------


def average(
    values: Sequence[float | int],
    weights: Sequence[float | int] | None = None,
) -> float:
    """Calculate the (weighted) average of a sequence.

    Args:
        values: Sequence of numeric values.
        weights: Optional weights (same length as *values*).

    Returns:
        The average.

    Raises:
        ValueError: If *values* is empty or *weights* length mismatch.
    """
    if not values:
        raise ValueError("Cannot compute average of empty sequence")
    if weights is not None:
        if len(weights) != len(values):
            raise ValueError(f"Weights length ({len(weights)}) != values length ({len(values)})")
        total_weight = sum(weights)
        if total_weight == 0:
            raise ValueError("Sum of weights is zero")
        return sum(v * w for v, w in zip(values, weights)) / total_weight
    return sum(values) / len(values)


# ---------------------------------------------------------------------------
# Min/Max
# ---------------------------------------------------------------------------


def min_max(values: Sequence[float | int]) -> tuple[float | int, float | int]:
    """Return the minimum and maximum of a sequence.

    Args:
        values: Sequence of numeric values.

    Returns:
        Tuple ``(min, max)``.

    Raises:
        ValueError: If *values* is empty.
    """
    if not values:
        raise ValueError("Cannot compute min/max of empty sequence")
    return (min(values), max(values))


# ---------------------------------------------------------------------------
# Distance
# ---------------------------------------------------------------------------


def distance(
    x1: float | int,
    y1: float | int,
    x2: float | int,
    y2: float | int,
) -> float:
    """Euclidean distance between two 2D points.

    Args:
        x1, y1: First point coordinates.
        x2, y2: Second point coordinates.

    Returns:
        Euclidean distance.
    """
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


# ---------------------------------------------------------------------------
# Normalize
# ---------------------------------------------------------------------------


def normalize(
    value: float | int,
    min_val: float | int,
    max_val: float | int,
    new_min: float | int = 0.0,
    new_max: float | int = 1.0,
) -> float:
    """Normalize a value from one range to another.

    Args:
        value: Value to normalize.
        min_val: Current range minimum.
        max_val: Current range maximum.
        new_min: Target range minimum (default: 0.0).
        new_max: Target range maximum (default: 1.0).

    Returns:
        Normalized value.

    Raises:
        ZeroDivisionError: If *min_val* == *max_val*.
    """
    if min_val == max_val:
        raise ZeroDivisionError(
            f"Cannot normalize: min_val ({min_val}) == max_val ({max_val})"
        )
    normalized = (float(value) - float(min_val)) / (float(max_val) - float(min_val))
    return normalized * (float(new_max) - float(new_min)) + float(new_min)


# ---------------------------------------------------------------------------
# Safe Division
# ---------------------------------------------------------------------------


def safe_division(
    numerator: float | int,
    denominator: float | int,
    default: float | None = None,
) -> float:
    """Divide two numbers safely.

    Args:
        numerator: The numerator.
        denominator: The denominator.
        default: Return value on zero division. If None, raises error.

    Returns:
        Division result, or *default* if denominator is zero.

    Raises:
        ZeroDivisionError: If *denominator* is zero and *default* is None.
    """
    if denominator == 0:
        if default is not None:
            logger.debug("Division by zero, returning default: %s", default)
            return float(default)
        raise ZeroDivisionError("Division by zero")
    return float(numerator) / float(denominator)


# ---------------------------------------------------------------------------
# Rounding
# ---------------------------------------------------------------------------


def round_to(
    value: float | int,
    decimals: int = 0,
    method: str = "standard",
) -> float:
    """Round a value using the specified rounding method.

    Args:
        value: Value to round.
        decimals: Decimal places (default: 0).
        method: ``"standard"`` (default), ``"floor"``, or ``"ceil"``.

    Returns:
        Rounded value.

    Raises:
        ValueError: If *method* is unknown.

    Example:
        >>> round_to(3.14159, 2)
        3.14
    """
    if method == "standard":
        return round(value, decimals)
    if method == "floor":
        factor = 10.0 ** decimals
        return math.floor(float(value) * factor) / factor
    if method == "ceil":
        factor = 10.0 ** decimals
        return math.ceil(float(value) * factor) / factor
    raise ValueError(f"Unknown rounding method: {method!r}. Use 'standard', 'floor', or 'ceil'.")


# ---------------------------------------------------------------------------
# Median
# ---------------------------------------------------------------------------


def median(values: Sequence[float | int]) -> float:
    """Compute the median of a sequence.

    Args:
        values: Sequence of numeric values.

    Returns:
        Median value.

    Raises:
        ValueError: If *values* is empty.
    """
    if not values:
        raise ValueError("Cannot compute median of empty sequence")
    return float(statistics.median(values))


# ---------------------------------------------------------------------------
# Variance
# ---------------------------------------------------------------------------


def variance(values: Sequence[float | int], ddof: int = 0) -> float:
    """Compute the variance of a sequence.

    Args:
        values: Sequence of numeric values.
        ddof: Delta degrees of freedom (0 = population, 1 = sample).

    Returns:
        Variance.

    Raises:
        ValueError: If *values* is empty or has insufficient elements
            for the given *ddof*.
    """
    if not values:
        raise ValueError("Cannot compute variance of empty sequence")
    return float(statistics.variance(values, xbar=None) if ddof == 1 and len(values) > 1
                 else statistics.pvariance(values))


# ---------------------------------------------------------------------------
# Standard Deviation
# ---------------------------------------------------------------------------


def standard_deviation(values: Sequence[float | int], ddof: int = 0) -> float:
    """Compute the standard deviation of a sequence.

    Args:
        values: Sequence of numeric values.
        ddof: Delta degrees of freedom (0 = population, 1 = sample).

    Returns:
        Standard deviation.

    Raises:
        ValueError: If *values* is empty or has insufficient elements.
    """
    if not values:
        raise ValueError("Cannot compute stddev of empty sequence")
    return math.sqrt(variance(values, ddof=ddof))
