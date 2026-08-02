"""VisionOps AI — Business Calculators Package.

Deterministic, pure domain calculations used by the business engines
(KPI engine, summary engine, etc.).

Contents (lazily importable):

- :mod:`backend.business.calculators.statistics` — numeric-safety core
  and reusable descriptive statistics.
- :mod:`backend.business.calculators.loading_time` — loading/unloading
  durations from real timestamps.
- :mod:`backend.business.calculators.waiting_time` — waiting durations
  from real timestamps.
- :mod:`backend.business.calculators.utilization` — utilization,
  occupancy and capacity calculations.
- :mod:`backend.business.calculators.productivity` — productivity,
  throughput and task-completion calculations.

No calculation is executed at import time; importing this package has no
filesystem or AI side effects.
"""

from __future__ import annotations

__all__ = [
    "statistics",
    "loading_time",
    "waiting_time",
    "utilization",
    "productivity",
]

