"""VisionOps AI — Worker Safety Rules.

Deterministic rules for worker-related domain conditions that are
**actually supported** by the runtime data contract.

Supported signals
-----------------
* **worker presence** — detections classified as ``"person"`` (the
  runtime detection contract maps workers to the generic ``person``
  class).
* **worker density per zone** — number of active worker (``person``)
  detections compared with the configured
  ``worker_safety.max_workers_per_zone``.

Unsupported signals (never fabricated)
--------------------------------------
* **PPE / safety-helmet / safety-vest detection** — the runtime
  :class:`~backend.schemas.common.DetectionClass` enum does **not**
  include ``helmet``, ``safety_vest``, or ``box`` classes.  Although
  ``ai_config.yaml`` lists ``helmet`` and ``safety_vest``, the runtime
  enum and the analysis-service allow-list omit them, so PPE rules
  remain dormant and return a deterministic "unsupported" outcome.
* **restricted-zone violations** — requires polygon zone geometry not
  present in detection/tracking data.
* **sensitive worker attributes** — no personal or behavioural
  attributes are ever inferred.

See the final report for recommended external contract changes.
"""

from __future__ import annotations

from typing import Any

from backend.business.rules import BusinessRulesConfig, RuleInput, RuleResult
from backend.schemas.common import Severity

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "WORKER_CLASS",
    "DEFAULT_MAX_WORKERS_PER_ZONE",
    "count_workers",
    "evaluate_worker_density",
    "evaluate_missing_ppe",
    "evaluate_zone_violation",
]

#: Detection class name for workers.
WORKER_CLASS: str = "person"

#: Safe default maximum workers per zone when configuration is absent.
DEFAULT_MAX_WORKERS_PER_ZONE: int = 5

#: PPE classes optionally present in some configurations; the runtime
#: detection contract does not include them.
_PPE_CLASSES: frozenset[str] = frozenset({"helmet", "safety_vest"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def count_workers(detections: list[Any]) -> int:
    """Count detection records classified as workers (``person``).

    Args:
        detections: Sequence of detection records (mappings supported).

    Returns:
        Number of worker detections (>= 0).
    """
    count = 0
    for det in detections or []:
        if isinstance(det, dict):
            cls = str(det.get("class_name", "")).strip().lower()
        else:
            cls = str(getattr(det, "class_name", "")).strip().lower()
        if cls == WORKER_CLASS:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Supported rules
# ---------------------------------------------------------------------------


def evaluate_worker_density(
    ctx: RuleInput,
    config: BusinessRulesConfig | None = None,
) -> RuleResult:
    """Evaluate whether worker density in the zone exceeds the limit.

    Args:
        ctx: Rule input context containing ``detections``.
        config: Optional business-rules configuration.  Reads
            ``worker_safety.max_workers_per_zone``.

    Returns:
        A :class:`RuleResult` with ``triggered=True`` when the number of
        workers exceeds the configured limit.
    """
    rules = config or BusinessRulesConfig()
    max_raw = rules.get(
        "worker_safety", "max_workers_per_zone", DEFAULT_MAX_WORKERS_PER_ZONE
    )
    try:
        max_count = int(max_raw)
    except (TypeError, ValueError):
        max_count = DEFAULT_MAX_WORKERS_PER_ZONE
    if max_count < 1:
        max_count = DEFAULT_MAX_WORKERS_PER_ZONE

    workers = count_workers(ctx.detections or [])
    if workers > max_count:
        return RuleResult(
            triggered=True,
            rule="worker.density",
            severity=Severity.MEDIUM,
            message=(
                f"Worker density exceeded: {workers} workers "
                f"(max {max_count} per zone)."
            ),
            details={
                "worker_count": workers,
                "max_workers_per_zone": max_count,
                "zone": ctx.zone,
            },
        )

    return RuleResult(
        triggered=False,
        rule="worker.density",
        severity=Severity.LOW,
        message="Worker density within limits.",
        details={"worker_count": workers, "max_workers_per_zone": max_count},
    )


# ---------------------------------------------------------------------------
# Unsupported rules (deterministic "not supported" outcomes)
# ---------------------------------------------------------------------------


def evaluate_missing_ppe(
    ctx: RuleInput,
    config: BusinessRulesConfig | None = None,
) -> RuleResult:
    """Return a deterministic *unsupported* result for missing PPE.

    The runtime detection contract does not include the ``helmet`` /
    ``safety_vest`` classes, so missing-PPE alerts cannot be evaluated
    with real data.  This rule never fabricates a PPE violation.

    Args:
        ctx: Rule input context (unused).
        config: Unused.

    Returns:
        A :class:`RuleResult` with ``triggered=False`` and
        ``reason='unsupported'``.
    """
    return RuleResult(
        triggered=False,
        rule="worker.missing_ppe",
        severity=Severity.LOW,
        message=(
            "Missing-PPE detection requires helmet/safety_vest classes "
            "that the runtime detection contract does not provide."
        ),
        details={"reason": "unsupported", "missing_classes": sorted(_PPE_CLASSES)},
    )


def evaluate_zone_violation(
    ctx: RuleInput,
    config: BusinessRulesConfig | None = None,
) -> RuleResult:
    """Return a deterministic *unsupported* result for zone violations.

    Restricted-zone violation detection requires polygon zone geometry
    that is not present in the detection/tracking data contract.

    Args:
        ctx: Rule input context (unused).
        config: Unused.

    Returns:
        A :class:`RuleResult` with ``triggered=False`` and
        ``reason='unsupported'``.
    """
    return RuleResult(
        triggered=False,
        rule="worker.zone_violation",
        severity=Severity.LOW,
        message=(
            "Restricted-zone violation detection requires polygon zone "
            "geometry not present in the data contract."
        ),
        details={"reason": "unsupported", "missing_signal": "zone_geometry"},
    )

