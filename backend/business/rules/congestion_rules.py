"""VisionOps AI — Congestion Rules.

Deterministic evaluation of congestion conditions based on the active
object count in a frame/zone.

Congestion levels are derived from the configured
``congestion.congestion_threshold`` and the ``congestion.levels`` ratios
in ``backend/config/business_rules.yaml``:

* low      — object count <  ``low * threshold``
* moderate — object count >= ``moderate * threshold``
* high     — object count >= ``high * threshold``
* critical — object count >= ``critical * threshold``

The threshold and level ratios are loaded from configuration; when the
configuration is unavailable, documented safe defaults are used.  Rules
never persist anything — they only evaluate state.
"""

from __future__ import annotations

from backend.business.rules import BusinessRulesConfig, RuleInput, RuleResult
from backend.schemas.common import Severity

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "DEFAULT_CONGESTION_THRESHOLD",
    "congestion_level",
    "evaluate_congestion",
]

#: Safe default congestion threshold used only when the YAML
#: configuration is unavailable.
DEFAULT_CONGESTION_THRESHOLD: int = 10

#: Safe default congestion level ratios relative to the threshold.
_DEFAULT_LEVELS: dict[str, float] = {
    "low": 0.5,
    "moderate": 0.75,
    "high": 1.0,
    "critical": 1.5,
}

#: Severity assigned to each congestion level.
_LEVEL_SEVERITY: dict[str, Severity] = {
    "low": Severity.LOW,
    "moderate": Severity.MEDIUM,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
}


# ---------------------------------------------------------------------------
# Level evaluation
# ---------------------------------------------------------------------------


def _read_levels(config: BusinessRulesConfig) -> dict[str, float]:
    """Read congestion level ratios from configuration.

    Args:
        config: Business-rules configuration.

    Returns:
        Mapping of level name -> ratio (normalised, positive).  Falls
        back to :data:`_DEFAULT_LEVELS` when configuration is missing.
    """
    levels_cfg = config.get("congestion", "levels", {})
    if not isinstance(levels_cfg, dict):
        return dict(_DEFAULT_LEVELS)

    levels: dict[str, float] = {}
    for name in ("low", "moderate", "high", "critical"):
        raw = levels_cfg.get(name, _DEFAULT_LEVELS[name])
        try:
            ratio = float(raw)
        except (TypeError, ValueError):
            ratio = _DEFAULT_LEVELS[name]
        levels[name] = ratio if ratio > 0 else _DEFAULT_LEVELS[name]
    return levels


def congestion_level(
    object_count: int,
    threshold: int = DEFAULT_CONGESTION_THRESHOLD,
    levels: dict[str, float] | None = None,
) -> str:
    """Return the congestion level for a given object count.

    Args:
        object_count: Active object count (non-negative integer).
        threshold: Congestion threshold object count.
        levels: Optional level-ratio mapping (defaults to the documented
            ratios).

    Returns:
        One of ``"low"``, ``"moderate"``, ``"high"`` or ``"critical"``.

    Raises:
        ValueError: If *object_count* or *threshold* is negative.
    """
    if isinstance(object_count, bool) or not isinstance(object_count, int):
        raise ValueError("object_count must be a non-negative integer.")
    if object_count < 0:
        raise ValueError("object_count must be a non-negative integer.")
    if threshold <= 0:
        raise ValueError("threshold must be a positive integer.")

    ratios = levels or _DEFAULT_LEVELS

    # Critical first (highest ratio), descending.
    critical_ratio = max(ratios.get("critical", _DEFAULT_LEVELS["critical"]), _DEFAULT_LEVELS["critical"])
    if object_count >= critical_ratio * threshold:
        return "critical"

    high_ratio = max(ratios.get("high", _DEFAULT_LEVELS["high"]), _DEFAULT_LEVELS["high"])
    if object_count >= high_ratio * threshold:
        return "high"

    moderate_ratio = max(ratios.get("moderate", _DEFAULT_LEVELS["moderate"]), _DEFAULT_LEVELS["moderate"])
    if object_count >= moderate_ratio * threshold:
        return "moderate"

    return "low"


def evaluate_congestion(
    ctx: RuleInput,
    config: BusinessRulesConfig | None = None,
) -> RuleResult:
    """Evaluate whether the input state qualifies as congestion.

    The object count is taken from ``ctx.object_count`` (when supplied)
    — otherwise it is derived from the number of detection records.

    Args:
        ctx: Rule input context.
        config: Optional business-rules configuration.

    Returns:
        A :class:`RuleResult` describing the congestion level.  Always
        returns a result with ``triggered=False`` for empty or zero-count
        input (no congestion).
    """
    rules = config or BusinessRulesConfig()
    threshold_raw = rules.get(
        "congestion", "congestion_threshold", DEFAULT_CONGESTION_THRESHOLD
    )
    try:
        threshold = int(threshold_raw)
    except (TypeError, ValueError):
        threshold = DEFAULT_CONGESTION_THRESHOLD
    if threshold <= 0:
        threshold = DEFAULT_CONGESTION_THRESHOLD

    if ctx.object_count is not None:
        count = ctx.object_count
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            count = len(ctx.detections or [])
    else:
        count = len(ctx.detections or [])

    if count <= 0:
        return RuleResult(
            triggered=False,
            rule="congestion.evaluate",
            severity=Severity.LOW,
            message="No congestion — zero active objects.",
            details={"object_count": 0, "threshold": threshold},
        )

    level = congestion_level(count, threshold=threshold)
    triggered = level in {"moderate", "high", "critical"}
    return RuleResult(
        triggered=triggered,
        rule=f"congestion.{level}",
        severity=_LEVEL_SEVERITY[level],
        message=(
            f"Congestion level '{level}': {count} active objects "
            f"(threshold {threshold})."
        ),
        details={
            "object_count": count,
            "threshold": threshold,
            "level": level,
        },
    )

