"""VisionOps AI — Productivity Calculator.

Deterministic, pure calculations for operational productivity.

Every score has an explicit, data-derived formula:

* ``productivity_rate``     = productive_time / total_time * 100
* ``throughput``            = units / observation_period
* ``productivity_index``    = actual / target * 100   (percent of target)
* ``task_completion_rate``  = completed_tasks / total_tasks * 100

All denominators are protected against zero/empty input.  No arbitrary
productivity value is ever fabricated.
"""

from __future__ import annotations

from backend.exceptions import ValidationError
from backend.business.calculators.statistics import as_float

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "productivity_rate",
    "throughput",
    "productivity_index",
    "task_completion_rate",
]


def productivity_rate(
    productive_time: float | int,
    total_time: float | int,
) -> float:
    """Return productive time as a percentage of total time.

    Formula:
        ``percent = (productive_time / total_time) * 100``

    Args:
        productive_time: Time spent on productive work, in the same unit
            as *total_time* (>= 0).
        total_time: Total observation time in the same unit (> 0).

    Returns:
        Productivity percentage in ``[0.0, 100.0]``.

    Raises:
        ValidationError: If *total_time* is zero, negative, or
            non-finite, or *productive_time* is negative.
    """
    total = as_float(total_time, name="total_time")
    if total <= 0.0:
        raise ValidationError(
            "total_time must be positive for a productivity rate."
        )

    productive = as_float(productive_time, name="productive_time")
    if productive < 0.0:
        raise ValidationError("productive_time must be non-negative.")
    return round(min(productive / total, 1.0) * 100.0, 2)


def throughput(
    units: float | int,
    observation_period: float | int,
) -> float:
    """Return throughput — units completed per observation period.

    Formula:
        ``rate = units / observation_period``

    Args:
        units: Number of completed units (>= 0).
        observation_period: Observation duration in seconds (> 0).

    Returns:
        Throughput in units per second.

    Raises:
        ValidationError: If *observation_period* is zero, negative, or
            non-finite, or *units* is negative.
    """
    period = as_float(observation_period, name="observation_period")
    if period <= 0.0:
        raise ValidationError(
            "observation_period must be positive for throughput."
        )

    unit_count = as_float(units, name="units")
    if unit_count < 0.0:
        raise ValidationError("units must be non-negative.")
    return round(unit_count / period, 4)


def productivity_index(
    actual: float | int,
    target: float | int,
) -> float:
    """Return productivity as a percentage of a target value.

    Formula:
        ``percent = (actual / target) * 100``

    Args:
        actual: Actual measured value (>= 0).
        target: Target value (> 0).

    Returns:
        Productivity index in percent (unbounded; values >= 100 mean the
        target was exceeded).

    Raises:
        ValidationError: If *target* is zero, negative, or non-finite,
            or *actual* is negative.
    """
    target_val = as_float(target, name="target")
    if target_val <= 0.0:
        raise ValidationError(
            "target must be positive for a productivity index."
        )

    actual_val = as_float(actual, name="actual")
    if actual_val < 0.0:
        raise ValidationError("actual must be non-negative.")
    return round((actual_val / target_val) * 100.0, 2)


def task_completion_rate(
    completed_tasks: float | int,
    total_tasks: float | int,
) -> float:
    """Return the task completion rate as a percentage.

    Formula:
        ``percent = (completed_tasks / total_tasks) * 100``

    Args:
        completed_tasks: Number of completed tasks (>= 0).
        total_tasks: Total number of tasks (> 0).

    Returns:
        Task completion percentage in ``[0.0, 100.0]``.

    Raises:
        ValidationError: If *total_tasks* is zero, negative, or
            non-finite, or *completed_tasks* is negative.
    """
    total = as_float(total_tasks, name="total_tasks")
    if total <= 0.0:
        raise ValidationError(
            "total_tasks must be positive for a completion rate."
        )

    completed = as_float(completed_tasks, name="completed_tasks")
    if completed < 0.0:
        raise ValidationError("completed_tasks must be non-negative.")
    return round(min(completed / total, 1.0) * 100.0, 2)

