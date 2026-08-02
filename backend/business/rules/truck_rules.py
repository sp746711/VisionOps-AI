"""VisionOps AI — Truck Operation Rules.

Deterministic truck-related domain conditions derived only from the
actual tracking/detection/event data contract.

Supported signals
-----------------
* **truck presence** — detections classified as ``"truck"`` (from
  :class:`~backend.schemas.common.DetectionClass`).
* **truck dwell/waiting duration** — computed from real timestamps on
  event records (e.g. ``created_at``).  A truck that remains present,
  or a queued/docked truck whose recorded interval exceeds the
  configured timeout, triggers a rule.

The following are **not** supported by the data contract and are never
inferred: truck speed, lane violations, or trailer-verification state.

Thresholds come from ``truck`` section of the business-rules YAML
(``queue_timeout``, ``dock_dwell_timeout``).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.business.rules import BusinessRulesConfig, RuleInput, RuleResult
from backend.schemas.common import Severity

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "TRUCK_CLASS",
    "count_trucks",
    "evaluate_truck_dwell",
    "truck_dwell_seconds",
]

#: Detection class name for trucks.
TRUCK_CLASS: str = "truck"

#: Default queue timeout (seconds) when configuration is absent.
_DEFAULT_QUEUE_TIMEOUT: float = 900.0

#: Default dock dwell timeout (seconds) when configuration is absent.
_DEFAULT_DOCK_DWELL_TIMEOUT: float = 1200.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def count_trucks(detections: list[Any]) -> int:
    """Count detection records classified as trucks.

    Args:
        detections: Sequence of detection records (mappings supported).

    Returns:
        Number of truck detections (>= 0).
    """
    count = 0
    for det in detections or []:
        if isinstance(det, dict):
            cls = str(det.get("class_name", "")).strip().lower()
        else:
            cls = str(getattr(det, "class_name", "")).strip().lower()
        if cls == TRUCK_CLASS:
            count += 1
    return count


def _coerce_utc(value: datetime | str | None) -> datetime | None:
    """Normalise a timestamp to timezone-aware UTC, else ``None``."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def truck_dwell_seconds(
    start: datetime | str | None,
    end: datetime | str | None,
) -> float | None:
    """Return the dwell duration (seconds) between two real timestamps.

    Args:
        start: Dwell start timestamp.
        end: Dwell end timestamp.

    Returns:
        Non-negative dwell duration in seconds, or ``None`` if either
        timestamp is missing/malformed.  A reversed interval yields
        ``0.0`` (never negative).
    """
    start_dt = _coerce_utc(start)
    end_dt = _coerce_utc(end)
    if start_dt is None or end_dt is None:
        return None
    return float(max((end_dt - start_dt).total_seconds(), 0.0))


def evaluate_truck_dwell(
    ctx: RuleInput,
    config: BusinessRulesConfig | None = None,
) -> RuleResult:
    """Evaluate whether a truck dwell/queue interval exceeded its limit.

    The dwell interval is derived from event records.  An event whose
    ``event_type`` contains ``queue`` or ``dock_dwell`` provides
    ``created_at`` / ``timestamp``; the interval is measured between
    consecutive matching events where both timestamps are present.

    Args:
        ctx: Rule input context containing ``events``.
        config: Optional business-rules configuration.  Reads
            ``truck.queue_timeout`` and ``truck.dock_dwell_timeout``.

    Returns:
        A :class:`RuleResult` describing whether any truck
        queue/dwell interval exceeded its configured timeout.
    """
    rules = config or BusinessRulesConfig()
    queue_timeout = _timeout(rules, "queue_timeout", _DEFAULT_QUEUE_TIMEOUT)
    dwell_timeout = _timeout(
        rules, "dock_dwell_timeout", _DEFAULT_DOCK_DWELL_TIMEOUT
    )

    events = ctx.events or []
    dwell_events: list[dict[str, Any]] = []
    for evt in events or []:
        if isinstance(evt, dict):
            event_type = str(evt.get("event_type", "")).strip().lower()
            rec = evt
        else:
            event_type = str(getattr(evt, "event_type", "")).strip().lower()
            rec = evt.to_dict()
        if "queue" in event_type or "dwell" in event_type:
            dwell_events.append(rec)

    if not dwell_events:
        return RuleResult(
            triggered=False,
            rule="truck.dwell",
            severity=Severity.LOW,
            message="No truck queue/dwell events.",
            details={"queue_timeout_s": queue_timeout, "dwell_timeout_s": dwell_timeout},
        )

    for rec in dwell_events:
        start_ts = _coerce_utc(rec.get("timestamp") or rec.get("created_at"))
        if start_ts is None:
            continue
        event_type = str(rec.get("event_type", "")).strip().lower()
        # The dwell/queue interval is compared against the matching
        # timeout based on event-type semantics.
        timeout = dwell_timeout if "dwell" in event_type else queue_timeout

        end_ts = _coerce_utc(
            rec.get("ended_at") or rec.get("updated_at") or rec.get("end_time")
        )
        if end_ts is None:
            # Single-event, no explicit end: if the event carries a
            # positive recorded duration we use it; otherwise skip.
            recorded = rec.get("duration_seconds")
            try:
                duration = float(recorded) if recorded is not None else None
            except (TypeError, ValueError):
                duration = None
            if duration is None or duration < 0:
                continue
        else:
            duration = max((end_ts - start_ts).total_seconds(), 0.0)

        if duration > timeout:
            return RuleResult(
                triggered=True,
                rule="truck.dwell",
                severity=Severity.HIGH,
                message=(
                    f"Truck {event_type} exceeded limit: {duration:.1f}s "
                    f"(limit {timeout:.1f}s)."
                ),
                details={
                    "event_type": event_type,
                    "duration_s": round(duration, 2),
                    "timeout_s": timeout,
                },
            )

    return RuleResult(
        triggered=False,
        rule="truck.dwell",
        severity=Severity.LOW,
        message="No truck queue/dwell interval exceeded its limit.",
        details={"queue_timeout_s": queue_timeout, "dwell_timeout_s": dwell_timeout},
    )


def _timeout(rules: BusinessRulesConfig, key: str, default: float) -> float:
    """Read a numeric timeout from configuration with a safe fallback."""
    raw = rules.get("truck", key, default)
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default

