"""VisionOps AI — Alert Trigger Rules.

Deterministic, reusable alert-trigger conditions used by the
:class:`~backend.business.alert_engine.AlertEngine`.

This module decides *whether an alert condition exists* and the
appropriate severity/message.  It never persists alerts and never sends
notifications — that belongs to the alert/service layer.

Supported conditions (all data-derived):

* **unknown / unauthorized class present** with confidence above a
  configurable threshold.  The historical test contract uses
  ``class_name == "unauthorized_person"`` with confidence ``0.95``;
  any class outside the runtime detection contract that appears with
  sufficient confidence triggers an alert.
* **high / critical severity event** present in the event stream.

Alert deduplication is intentionally *not* stateful here; the engine
layer owns suppression windows (see ``alerts.suppression`` in
:mod:`backend.business.rules`).
"""

from __future__ import annotations

from typing import Any

from backend.business.rules import (
    BusinessRulesConfig,
    RuleInput,
    RuleResult,
    SUPPORTED_CLASSES,
)
from backend.schemas.common import DetectionClass, Severity

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "DEFAULT_ALERT_CONFIDENCE",
    "evaluate_unknown_class_alert",
    "evaluate_high_severity_event_alert",
    "severity_from_string",
]

#: Default minimum confidence for an unknown-class alert when the YAML
#: configuration is unavailable.
DEFAULT_ALERT_CONFIDENCE: float = 0.6

#: Detection class values the backend actually supports at runtime.
_SUPPORTED_VALUES: frozenset[str] = (
    SUPPORTED_CLASSES | {cls.value for cls in DetectionClass}
)

#: Event types that indicate a high/critical operational condition.
_HIGH_RISK_EVENT_TYPES: frozenset[str] = frozenset(
    {"temperature_breach", "spoilage_risk", "anomaly", "critical"}
)


# ---------------------------------------------------------------------------
# Severity mapping
# ---------------------------------------------------------------------------


def severity_from_string(value: str | None) -> Severity:
    """Coerce a raw severity string into a :class:`Severity` member.

    Args:
        value: Raw severity value (e.g. ``"high"``).

    Returns:
        The corresponding :class:`Severity` member; defaults to
        :attr:`Severity.LOW` for unknown/empty values.
    """
    if value is None:
        return Severity.LOW
    try:
        return Severity(str(value).strip().lower())
    except ValueError:
        return Severity.LOW


# ---------------------------------------------------------------------------
# Rule evaluations
# ---------------------------------------------------------------------------


def evaluate_unknown_class_alert(
    ctx: RuleInput,
    config: BusinessRulesConfig | None = None,
) -> RuleResult:
    """Evaluate whether an unknown/unauthorized class triggers an alert.

    Args:
        ctx: Rule input context containing ``detections``.
        config: Optional business-rules configuration.  The minimum
            confidence threshold is read from
            ``worker_safety.alert_confidence``, falling back to
            :data:`DEFAULT_ALERT_CONFIDENCE`.

    Returns:
        A :class:`RuleResult` with ``triggered=True`` when at least one
        detection (a) uses a class outside the runtime detection
        contract or is ``"unauthorized_person"``, and (b) has confidence
        >= the configured threshold.
    """
    rules = config or BusinessRulesConfig()
    threshold = float(
        rules.get("worker_safety", "alert_confidence", DEFAULT_ALERT_CONFIDENCE)
    )

    for det in ctx.detections or []:
        if not isinstance(det, dict):
            continue
        cls = str(det.get("class_name", "")).strip().lower()
        if not cls:
            continue
        try:
            confidence = float(det.get("confidence", 0.0))
        except (TypeError, ValueError):
            continue

        is_unknown = cls not in _SUPPORTED_VALUES or cls == "unauthorized_person"
        if is_unknown and confidence >= threshold:
            return RuleResult(
                triggered=True,
                rule="alert.unknown_class",
                severity=Severity.HIGH,
                message=(
                    f"Detection of unsupported/unauthorized class "
                    f"'{cls}' with confidence {confidence:.2f}."
                ),
                details={"class_name": cls, "confidence": confidence},
            )

    return RuleResult(
        triggered=False,
        rule="alert.unknown_class",
        severity=Severity.LOW,
        message="No unsupported/unauthorized class detected.",
    )


def evaluate_high_severity_event_alert(
    ctx: RuleInput,
    config: BusinessRulesConfig | None = None,
) -> RuleResult:
    """Evaluate whether a high/critical event should raise an alert.

    Args:
        ctx: Rule input context containing ``events``.
        config: Unused; retained for a consistent rule signature.

    Returns:
        A :class:`RuleResult` with ``triggered=True`` when at least one
        event has severity ``high``/``critical`` or a high-risk event
        type.
    """
    for evt in ctx.events or []:
        if isinstance(evt, dict):
            severity = str(evt.get("severity", "")).strip().lower()
            event_type = str(evt.get("event_type", "")).strip().lower()
        else:
            severity = str(getattr(evt, "severity", "")).strip().lower()
            event_type = str(getattr(evt, "event_type", "")).strip().lower()

        if severity in {"high", "critical"} or event_type in _HIGH_RISK_EVENT_TYPES:
            return RuleResult(
                triggered=True,
                rule="alert.high_severity_event",
                severity=severity_from_string(severity),
                message=(
                    f"High-severity event detected "
                    f"(type='{event_type}', severity='{severity}')."
                ),
                details={"event_type": event_type, "severity": severity},
            )

    return RuleResult(
        triggered=False,
        rule="alert.high_severity_event",
        severity=Severity.LOW,
        message="No high-severity events detected.",
    )


# ---------------------------------------------------------------------------
# Alert suppression window helper (deduplication)
# ---------------------------------------------------------------------------


def suppression_min_interval(config: BusinessRulesConfig | None = None) -> float:
    """Return the minimum interval (seconds) between repeated alerts.

    Reads ``alerts.suppression.min_interval`` from the business-rules
    configuration.  Returns a safe default of ``30`` seconds when the
    configuration is unavailable.

    Args:
        config: Optional business-rules configuration.

    Returns:
        Minimum interval in seconds (a positive finite float).
    """
    rules = config or BusinessRulesConfig()
    suppression = rules.get("alerts", "suppression", {})
    if isinstance(suppression, dict):
        value = suppression.get("min_interval", 30)
    else:
        value = 30
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 30.0
    if parsed <= 0:
        return 30.0
    return parsed

