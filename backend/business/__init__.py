"""VisionOps AI — Business Domain Layer.

This package converts validated AI/detection/event information into
meaningful operational intelligence:

    Video
      ↓
    backend/ai
      ↓
    Detections / Tracking
      ↓
    backend/business
      ├── Rules        (deterministic domain predicates)
      ├── Calculators  (deterministic operational metrics)
      ├── Events       (EventEngine → Event records)
      ├── Alerts       (AlertEngine → Alert records)
      ├── KPIs         (KPIEngine → KPI records)
      └── Summaries    (SummaryEngine → operational summaries)
      ↓
    backend/analytics
      ↓
    Services / Dashboard / Reports / Power BI

Public engines
--------------
- :class:`~backend.business.business_engine.BusinessEngine` — high-level
  facade orchestrating the sub-engines.
- :class:`~backend.business.event_engine.EventEngine` — converts domain
  conditions into standardized event records.
- :class:`~backend.business.alert_engine.AlertEngine` — evaluates
  conditions and creates standardized alert records.
- :class:`~backend.business.kpi_engine.KPIEngine` — computes operational
  KPIs from real data.
- :class:`~backend.business.summary_engine.SummaryEngine` — produces
  concise business summaries.

Import safety
-------------
Importing ``backend.business`` has **no side effects**: no storage
initialization, no file creation, no AI/model loading, and no business
processing.  Submodules are imported lazily via :pep:`562` so the
package import stays lightweight and side-effect free.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

# ---------------------------------------------------------------------------
# Lazy export registry — maps public name -> (module path, attribute name)
# ---------------------------------------------------------------------------

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "BusinessEngine": (
        "backend.business.business_engine",
        "BusinessEngine",
    ),
    "EventEngine": ("backend.business.event_engine", "EventEngine"),
    "AlertEngine": ("backend.business.alert_engine", "AlertEngine"),
    "KPIEngine": ("backend.business.kpi_engine", "KPIEngine"),
    "SummaryEngine": ("backend.business.summary_engine", "SummaryEngine"),
}

#: Public API of the business package.
__all__ = sorted(_LAZY_EXPORTS)

# Forward references for static type checkers and IDE autocompletion.
if TYPE_CHECKING:  # pragma: no cover
    from backend.business.alert_engine import AlertEngine as AlertEngine
    from backend.business.business_engine import BusinessEngine as BusinessEngine
    from backend.business.event_engine import EventEngine as EventEngine
    from backend.business.kpi_engine import KPIEngine as KPIEngine
    from backend.business.summary_engine import SummaryEngine as SummaryEngine


# ---------------------------------------------------------------------------
# PEP 562 lazy attribute access
# ---------------------------------------------------------------------------


def __getattr__(name: str) -> object:
    """Lazily import and return a public engine class by name.

    Args:
        name: The requested public engine name.

    Returns:
        The requested engine class.

    Raises:
        AttributeError: If *name* is not a known engine export.
    """
    entry = _LAZY_EXPORTS.get(name)
    if entry is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = entry
    module = importlib.import_module(module_name)
    return getattr(module, attribute_name)


def __dir__() -> list[str]:
    """Return the complete public attribute listing for IDE support.

    Returns:
        Sorted union of the module's own attributes and the lazily
        exported engine names.
    """
    return sorted({*globals().keys(), *_LAZY_EXPORTS})


