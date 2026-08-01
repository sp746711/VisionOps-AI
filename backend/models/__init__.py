"""VisionOps AI — Domain Model Package.

This package defines the pure, framework-free **domain models** used
internally across the VisionOps AI backend.  Models describe how
application data exists internally — they are *not* API request/response
schemas, *not* business logic, *not* services, *not* storage managers,
and *not* ORM/database models.

Every model in this package:

- is a :func:`dataclasses.dataclass` with ``slots=True`` (frozen where
  mutation should never occur),
- documents all attributes and invariants,
- provides ``to_dict()`` / ``from_dict()`` serialization helpers that
  integrate cleanly with the CSV/JSON storage and service layers,
- supports ``copy()`` and ``update()``,
- is hashable where appropriate,
- reuses existing project types (enums, value objects, exceptions,
  utilities) instead of redefining them.

Contents (lazily loaded):

- :class:`User` — authenticated application user.
- :class:`Video` — video upload/processing metadata record.
- :class:`Detection` — a single object detection result.
- :class:`Event` — a business-level event record.
- :class:`Alert` — a generated alert record.
- :class:`KPI` — a key performance indicator record.
- :class:`Analysis` — a detection-analysis result record.
- :class:`Report` — a generated report record.
- :class:`Settings` — application settings snapshot.

Lazy loading
------------
Submodules are imported on demand via :pep:`562` ``__getattr__``.  This
keeps the package import lightweight, avoids circular-import pitfalls
between the models and the rest of the backend, and allows individual
model modules to be imported independently (``import backend.models.user``).

Usage::

    from backend.models import User, Video, Detection

    video = Video.from_dict(record)
    payload = video.to_dict()
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

# ---------------------------------------------------------------------------
# Lazy export registry — maps public name -> (module path, attribute name)
# ---------------------------------------------------------------------------

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "User": ("backend.models.user", "User"),
    "Video": ("backend.models.video", "Video"),
    "Detection": ("backend.models.detection", "Detection"),
    "Event": ("backend.models.event", "Event"),
    "Alert": ("backend.models.alert", "Alert"),
    "KPI": ("backend.models.kpi", "KPI"),
    "Analysis": ("backend.models.analysis", "Analysis"),
    "Report": ("backend.models.report", "Report"),
    "Settings": ("backend.models.settings", "Settings"),
}

#: Public API of the models package.
__all__ = sorted(_LAZY_EXPORTS)

# Forward references for static type checkers and IDE autocompletion.
if TYPE_CHECKING:  # pragma: no cover
    from backend.models.alert import Alert as Alert
    from backend.models.analysis import Analysis as Analysis
    from backend.models.detection import Detection as Detection
    from backend.models.event import Event as Event
    from backend.models.kpi import KPI as KPI
    from backend.models.report import Report as Report
    from backend.models.settings import Settings as Settings
    from backend.models.user import User as User
    from backend.models.video import Video as Video


# ---------------------------------------------------------------------------
# PEP 562 lazy attribute access
# ---------------------------------------------------------------------------


def __getattr__(name: str) -> object:
    """Lazily import and return a model class by name.

    Invoked by Python only when *name* is not found as a regular module
    attribute.  Delegates to the registry :data:`_LAZY_EXPORTS` to
    import the owning submodule and return the requested attribute.

    Args:
        name: The requested public model name.

    Returns:
        The requested model class.

    Raises:
        AttributeError: If *name* is not a known model export.
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
        exported model names.
    """
    return sorted({*globals().keys(), *_LAZY_EXPORTS})

