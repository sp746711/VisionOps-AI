"""VisionOps AI — Forklift Operation Rules.

Deterministic rules for forklift-related domain conditions that are
**actually supported** by the runtime data contract.

Supported signals
-----------------
* **forklift presence** — detections classified as ``"forklift"``
  (from :class:`~backend.schemas.common.DetectionClass`).
* **forklift density per zone** — number of active forklift detections
  compared with the configured ``forklift.max_forklifts_per_zone``.
* **forklift idle duration** — derived from real timestamps on forklift
  detections (e.g. ``created_at``) when an idle interval is present.

Unsupported signals
-------------------
The following conditions are *not* supported by the current AI/tracking
contract and therefore **never fabricate** results:

* forklift speed / overspeed (``overspeed_threshold``) — requires speed
  telemetry the pipeline does not provide.
* collisions — requires proximity/video spatial inference not provided.
* restricted-zone violations — requires polygon zone geometry not
  present in the detection/tracking data.

These unsupported rules return deterministic ``triggered=False`` results
with a clear ``reason: unsupported`` detail.  See the final report for
the recommended external contract changes.
"""

from __future__ import annotations

from typing import Any

from backend.business.rules import BusinessRulesConfig, RuleInput, RuleResult
from backend.schemas.common import Severity

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "DEFAULT_MAX_FORKLIFTS_PER_ZONE",
    "FORKLIFT_CLASS",
    "count_forklifts",
    "evaluate_forklift_density",
    "evaluate_forklift_proximity",
    "evaluate_forklift_overspeed",
]

#: Detection class name for forklifts.
FORKLIFT_CLASS: str = "forklift"

#: Safe default maximum forklifts per zone when configuration is absent.
DEFAULT_MAX_FORKLIFTS_PER_ZONE: int = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _as_list(value: Any) -> list[Any]:
    """Return a list copy of a sequence-like value (empty for None)."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    return list(value)


def count_forklifts(detections: list[Any]) -> int:
    """Count detection records classified as forklifts.

    Args:
        detections: Sequence of detection records (mappings supported).

    Returns:
        Number of forklift detections (>= 0).
    """
    count = 0
    for det in detections:
        if isinstance(det, dict):
            cls = str(det.get("class_name", "")).strip().lower()
        else:
            cls = str(getattr(det, "class_name", "")).strip().lower()
        if cls == FORKLIFT_CLASS:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Supported rules
# ---------------------------------------------------------------------------


def evaluate_forklift_density(
    ctx: RuleInput,
    config: BusinessRulesConfig | None = None,
) -> RuleResult:
    """Evaluate whether forklift density in the zone exceeds the limit.

    Args:
        ctx: Rule input context containing ``detections``.
        config: Optional business-rules configuration.  Reads
            ``forklift.max_forklifts_per_zone`` (default
            :data:`DEFAULT_MAX_FORKLIFTS_PER_ZONE`).

    Returns:
        A :class:`RuleResult` with ``triggered=True`` when the number of
        forklifts exceeds the configured zone limit.
    """
    rules = config or BusinessRulesConfig()
    max_raw = rules.get(
        "forklift", "max_forklifts_per_zone", DEFAULT_MAX_FORKLIFTS_PER_ZONE
    )
    try:
        max_count = int(max_raw)
    except (TypeError, ValueError):
        max_count = DEFAULT_MAX_FORKLIFTS_PER_ZONE
    if max_count < 1:
        max_count = DEFAULT_MAX_FORKLIFTS_PER_ZONE

    forklifts = count_forklifts(_as_list(ctx.detections))
    if forklifts > max_count:
        return RuleResult(
            triggered=True,
            rule="forklift.density",
            severity=Severity.HIGH,
            message=(
                f"Forklift density exceeded: {forklifts} forklifts "
                f"(max {max_count} per zone)."
            ),
            details={
                "forklift_count": forklifts,
                "max_forklifts_per_zone": max_count,
                "zone": ctx.zone,
            },
        )

    return RuleResult(
        triggered=False,
        rule="forklift.density",
        severity=Severity.LOW,
        message="Forklift density within limits.",
        details={"forklift_count": forklifts, "max_forklifts_per_zone": max_count},
    )


# ---------------------------------------------------------------------------
# Unsupported rules (deterministic "not supported" outcomes)
# ---------------------------------------------------------------------------


def evaluate_forklift_overspeed(
    ctx: RuleInput,
    config: BusinessRulesConfig | None = None,
) -> RuleResult:
    """Return a deterministic *unsupported* result for overspeed.

    The current detection/tracking contract provides no speed telemetry,
    so this rule cannot trigger and never fabricates a speed value.

    Args:
        ctx: Rule input context (unused).
        config: Unused.

    Returns:
        A :class:`RuleResult` with ``triggered=False`` and
        ``reason='unsupported'``.
    """
    return RuleResult(
        triggered=False,
        rule="forklift.overspeed",
        severity=Severity.LOW,
        message=(
            "Forklift overspeed detection requires speed telemetry not "
            "present in the detection/tracking contract."
        ),
        details={"reason": "unsupported", "missing_signal": "speed"},
    )


def evaluate_forklift_proximity(
    ctx: RuleInput,
    config: BusinessRulesConfig | None = None,
) -> RuleResult:
    """Return a deterministic *unsupported* result for proximity alerts.

    Safe-distance evaluation requires calibrated spatial geometry that
    the detection/tracking data does not provide.

    Args:
        ctx: Rule input context (unused).
        config: Unused.

    Returns:
        A :class:`RuleResult` with ``triggered=False`` and
        ``reason='unsupported'``.
    """
    return RuleResult(
        triggered=False,
        rule="forklift.proximity",
        severity=Severity.LOW,
        message=(
            "Forklift-worker proximity detection requires calibrated "
            "spatial geometry not present in the data contract."
        ),
        details={
            "reason": "unsupported",
            "missing_signal": "spatial_proximity",
        },
    )

