"""VisionOps AI — Business Rules Package.

Deterministic domain predicates/evaluators used by the business engines.
Rules answer questions such as *"does this condition qualify as
congestion?"*; they never persist alerts, send notifications, or perform
side effects.

Shared value objects
--------------------
- :class:`RuleResult` — a single deterministic rule evaluation result.
- :class:`RuleInput` — input context container passed to rule functions.
- :class:`BusinessRulesConfig` — lazy loader for
  ``backend/config/business_rules.yaml``.

Configuration is loaded **lazily and safely**:

- the YAML file is read only on first access, never at import time;
- a missing/malformed file yields controlled safe defaults, so business
  logic remains deterministic and import-safe;
- ``backend.core.config`` is intentionally *not* imported (it creates
  managed directories at import time, which business imports must not do).

The runtime detection classes supported by the rest of the backend are
defined by :class:`backend.schemas.common.DetectionClass`.  Rule modules
that reference capabilities absent from that contract (such as PPE
helmet/vest classes) stay import-safe and report *unsupported* outcomes
rather than fabricating detections.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from backend.schemas.common import DetectionClass, Severity

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

#: Public API exported directly from this package root.
__all__ = [
    "RuleResult",
    "RuleInput",
    "BusinessRulesConfig",
    "DEFAULT_BUSINESS_RULES_PATH",
    "SUPPORTED_CLASSES",
    "UNSUPPORTED_CLASSES",
]

#: Rule modules re-exported lazily (per PEP 562) so importing the rules
#: package stays side-effect free and lightweight.
_LAZY_MODULES: dict[str, str] = {
    "alert_rules": "backend.business.rules.alert_rules",
    "congestion_rules": "backend.business.rules.congestion_rules",
    "forklift_rules": "backend.business.rules.forklift_rules",
    "loading_rules": "backend.business.rules.loading_rules",
    "truck_rules": "backend.business.rules.truck_rules",
    "worker_rules": "backend.business.rules.worker_rules",
}

# Forward references for static type checkers and IDE autocompletion.
if TYPE_CHECKING:  # pragma: no cover
    from backend.business.rules import alert_rules as alert_rules
    from backend.business.rules import congestion_rules as congestion_rules
    from backend.business.rules import forklift_rules as forklift_rules
    from backend.business.rules import loading_rules as loading_rules
    from backend.business.rules import truck_rules as truck_rules
    from backend.business.rules import worker_rules as worker_rules


def __getattr__(name: str) -> object:
    """Lazily import a rule submodule by name.

    Args:
        name: Attribute name being resolved.

    Returns:
        The requested rule submodule.

    Raises:
        AttributeError: If *name* is not a known rule module export.
    """
    module_name = _LAZY_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(module_name)
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    """Return the complete public attribute listing for IDE support."""
    return sorted({*globals().keys(), *_LAZY_MODULES})

#: Severity levels supported by rule evaluation (mirrors
#: :class:`~backend.schemas.common.Severity`).
SeverityLevel = Literal["low", "medium", "high", "critical"]

#: Absolute path to the business-rules YAML configuration file.
DEFAULT_BUSINESS_RULES_PATH: str = os.path.join(
    "backend", "config", "business_rules.yaml"
)


# ---------------------------------------------------------------------------
# RuleResult
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class RuleResult:
    """A deterministic, immutable rule-evaluation result.

    Attributes:
        triggered: Whether the rule condition is currently satisfied.
        rule: Stable machine-readable rule identifier (e.g.
            ``"congestion.high"``).
        severity: Associated severity
            (:class:`~backend.schemas.common.Severity`).
        message: Human-readable explanation of the result.
        details: Optional structured detail payload (e.g. observed value
            and threshold).  Defaults to an empty mapping.
    """

    triggered: bool
    rule: str
    severity: Severity = Severity.LOW
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Serialize the result to a plain dictionary.

        Returns:
            Dictionary with ``triggered``, ``rule``, ``severity``,
            ``message`` and ``details`` keys.
        """
        return {
            "triggered": self.triggered,
            "rule": self.rule,
            "severity": self.severity.value,
            "message": self.message,
            "details": dict(self.details),
        }


# ---------------------------------------------------------------------------
# RuleInput
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RuleInput:
    """Input context passed to rule evaluators.

    Rules receive a snapshot of the domain state they evaluate.  All
    attributes are optional so rules can be unit-tested with minimal
    data.

    Attributes:
        video_id: Optional video the input state belongs to.
        detections: Optional sequence of detection records (mappings or
            :class:`~backend.models.detection.Detection` instances).
        events: Optional sequence of event records (mappings or
            :class:`~backend.models.event.Event` instances).
        timestamp: Optional observation timestamp.
        object_count: Optional over-ride for the number of active
            objects in a zone/frame.
        zone: Optional zone identifier when spatial context exists.
    """

    video_id: str | None = None
    detections: list[Any] = field(default_factory=list)
    events: list[Any] = field(default_factory=list)
    timestamp: datetime | None = None
    object_count: int | None = None
    zone: str | None = None


# ---------------------------------------------------------------------------
# BusinessRulesConfig — lazy YAML loader
# ---------------------------------------------------------------------------


class BusinessRulesConfig:
    """Lazy, safe loader for ``backend/config/business_rules.yaml``.

    The YAML file is read once on first attribute access and cached.
    Missing or malformed files produce controlled, documented defaults so
    business evaluation remains deterministic and import-safe.

    Attributes:
        path: Absolute path of the YAML configuration file.
    """

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        """Initialise the lazy config loader.

        Args:
            path: Path to the YAML file.  When ``None``,
                :data:`DEFAULT_BUSINESS_RULES_PATH` is used (relative to
                the current working directory; safe to override in
                tests).
        """
        self.path: Path = Path(path or DEFAULT_BUSINESS_RULES_PATH)
        self._data: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        """Load and cache the YAML configuration.

        Returns:
            Mapping of configuration sections.  Always returns a dict
            (never raises for missing/malformed files).

        Raises:
            RuntimeError: If PyYAML is unavailable.  (PyYAML is a
                declared runtime companion for this backend, but the
                loader stays defensive.)
        """
        if self._data is not None:
            return self._data

        data: dict[str, Any] = {}
        try:
            import yaml  # Lazy import — no YAML dependency at import time
        except ImportError as exc:  # pragma: no cover — defensive
            raise RuntimeError(
                "PyYAML is required to load business rules configuration."
            ) from exc

        try:
            if self.path.is_file():
                loaded = yaml.safe_load(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data = loaded
        except (OSError, ValueError, yaml.YAMLError):
            # Missing/malformed configuration → controlled safe defaults.
            data = {}

        self._data = data
        return data

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def get(self, section: str, key: str | None = None, default: Any = None) -> Any:
        """Return a configuration value with an explicit fallback.

        Args:
            section: Top-level YAML section (e.g. ``"congestion"``).
            key: Optional key within the section.
            default: Default returned when the requested value is absent.

        Returns:
            The configured value, or *default*.
        """
        data = self._load()
        node = data.get(section, {}) if isinstance(data, dict) else {}
        if not isinstance(node, dict):
            return default
        if key is None:
            return node
        return node.get(key, default)

    def section(self, name: str, default: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return an entire configuration section.

        Args:
            name: Top-level YAML section name.
            default: Fallback mapping when the section is absent.

        Returns:
            The section mapping (never ``None``).
        """
        value = self.get(name)
        if isinstance(value, dict):
            return value
        return dict(default or {})

    @property
    def data(self) -> dict[str, Any]:
        """Return the full configuration mapping (lazy loaded)."""
        return self._load()

    def reload(self) -> None:
        """Drop the cached configuration so the next access re-reads the
        YAML file."""
        self._data = None


# ---------------------------------------------------------------------------
# Supported runtime detection classes
# ---------------------------------------------------------------------------

#: The set of detection classes the rest of the backend actually supports
#: at runtime (from :class:`~backend.schemas.common.DetectionClass`).
SUPPORTED_CLASSES: frozenset[str] = frozenset(
    {cls.value for cls in DetectionClass}
)

#: Classes that business rules reference but are NOT part of the runtime
#: detection contract.  Evaluators that rely on these return deterministic
#: "unsupported" outcomes; they never fabricate detections.
UNSUPPORTED_CLASSES: frozenset[str] = frozenset(
    {
        "helmet",
        "safety_vest",
        "box",
        "container",
    }
)

