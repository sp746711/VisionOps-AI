"""VisionOps AI — Utilization Calculator.

Deterministic, pure calculations for operational utilization.

The canonical project concept is::

    utilization = active_time / available_time * 100  (percent)

A zero or non-positive *available_time* yields ``0.0`` (a resource that
is never available is never "utilized").  Active time is clamped to the
available time so utilization can never exceed ``100%``.
"""

from __future__ import annotations

from backend.business.calculators.statistics import as_float, percentage

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "utilization_ratio",
    "utilization_rate",
    "occupancy_rate",
    "capacity_utilization",
]


def utilization_ratio(active_time: float | int, available_time: float | int) -> float:
    """Return utilization as a fraction of ``[0.0, 1.0]``.

    Args:
        active_time: Time the resource was actively used (seconds).
        available_time: Total time the resource was available (seconds).

    Returns:
        Utilization ratio between ``0.0`` and ``1.0`` (Python ``float``).
    """
    active = as_float(active_time, name="active_time")
    available = as_float(available_time, name="available_time")
    if available <= 0:
        return 0.0
    return float(min(active, available) / available)


def utilization_rate(
    active_time: float | int,
    available_time: float | int,
) -> float:
    """Return utilization as a percentage (``0.0`` – ``100.0``).

    Args:
        active_time: Time the resource was actively used (seconds).
        available_time: Total time the resource was available (seconds).

    Returns:
        Utilization percentage between ``0.0`` and ``100.0``.
    """
    return float(utilization_ratio(active_time, available_time) * 100.0)


def occupancy_rate(
    occupied_time: float | int,
    total_time: float | int,
) -> float:
    """Return occupancy as a percentage (``0.0`` – ``100.0``).

    This is the same underlying formula as :func:`utilization_rate` and
    is provided as an explicit domain alias for dock/zone occupancy.

    Args:
        occupied_time: Time the zone/resource was occupied (seconds).
        total_time: Total observation time (seconds).

    Returns:
        Occupancy percentage between ``0.0`` and ``100.0``.
    """
    return float(utilization_ratio(occupied_time, total_time) * 100.0)


def capacity_utilization(
    used_capacity: float | int,
    total_capacity: float | int,
) -> float:
    """Return capacity utilization as a percentage (``0.0`` – ``100.0``).

    Args:
        used_capacity: Capacity units actually used.
        total_capacity: Total installed capacity.

    Returns:
        Capacity utilization percentage between ``0.0`` and ``100.0``.
    """
    used = as_float(used_capacity, name="used_capacity")
    total = as_float(total_capacity, name="total_capacity")
    if total <= 0:
        return 0.0
    return float(percentage(used, total, default=0.0))

