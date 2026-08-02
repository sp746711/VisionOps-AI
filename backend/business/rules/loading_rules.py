"""VisionOps AI — Loading/Unloading Rules.

Deterministic rules for loading and unloading operations.

Loading activity is **only** inferred from explicit event records (e.g.
``event_type == "loading_start"`` / ``"loading_end"``, or
``"unloading_start"`` / ``"unloading_end"``) that carry real timestamps.
A truck or dock detection alone is **never** treated as evidence of
active loading — the project contract does not define that inference.

Supported signals
-----------------
* explicit loading/unloading start/end event pairs
* loading/unloading timeout evaluation against configured thresholds
  (``truck.loading_timeout`` / ``truck.unloading_timeout``)

The module never fabricates loading durations or infers activity from
mere object presence.
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
    "LOADING_START_TYPES",
    "LOADING_END_TYPES",
    "load_or_unload_events",
    "evaluate_loading_timeout",
]

#: Event types that mark the start of a loading/unloading operation.
LOADING_START_TYPES: frozenset[str] = frozenset(
    {"loading_start", "unloading_start"}
)

#: Event types that mark the end of a loading/unloading operation.
LOADING_END_TYPES: frozenset[str] = frozenset(
    {"loading_end", "unloading_end"}
)

#: Default loading timeout (seconds) when configuration is absent.
_DEFAULT_LOADING_TIMEOUT: float = 600.0

#: Default unloading timeout (seconds) when configuration is absent.
_DEFAULT_UNLOADING_TIMEOUT: float = 480.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def load_or_unload_events(events: list[Any]) -> list[dict[str, Any]]:
    """Return explicit loading/unloading event records as a normalised
    list of dictionaries.

    Args:
        events: Sequence of event records (mappings or objects).

    Returns:
        List of event dictionaries whose ``event_type`` is a
        loading/unloading event type.
    """
    result: list[dict[str, Any]] = []
    for evt in events or []:
        if isinstance(evt, dict):
            event_type = str(evt.get("event_type", ""))
        else:
            event_type = str(getattr(evt, "event_type", ""))
        if event_type.strip().lower() in (LOADING_START_TYPES | LOADING_END_TYPES):
            result.append(dict(evt) if isinstance(evt, dict) else evt.to_dict())
    return result


def evaluate_loading_timeout(
    ctx: RuleInput,
    config: BusinessRulesConfig | None = None,
) -> RuleResult:
    """Evaluate whether a loading/unloading operation exceeded its
    configured timeout.

    Only explicit start/end event pairs with valid timestamps are used.
    The start event must carry a ``created_at`` (or ``timestamp``)
    record; if no end event is present, no timeout is evaluated (an
    in-progress operation is not fabricated).

    Args:
        ctx: Rule input context containing ``events``.
        config: Optional business-rules configuration.  Reads
            ``truck.loading_timeout`` and ``truck.unloading_timeout``.

    Returns:
        A :class:`RuleResult` describing whether any operation exceeded
        its timeout.
    """
    rules = config or BusinessRulesConfig()
    loading_timeout = _timeout(rules, "loading_timeout", _DEFAULT_LOADING_TIMEOUT)
    unloading_timeout = _timeout(rules, "unloading_timeout", _DEFAULT_UNLOADING_TIMEOUT)

    events = load_or_unload_events(ctx.events or [])
    if not events:
        return RuleResult(
            triggered=False,
            rule="loading.timeout",
            severity=Severity.LOW,
            message="No explicit loading/unloading events.",
            details={"loading_timeout_s": loading_timeout, "unloading_timeout_s": unloading_timeout},
        )

    # Group events by (video_id, event_type-pair) as a simple heuristic.
    # For each start event, look for the matching end event and compute
    # the duration from real timestamps.
    starts = [
        e for e in events if e.get("event_type", "").strip().lower() in LOADING_START_TYPES
    ]
    for start in starts:
        start_ts = _coerce_utc(start.get("timestamp") or start.get("created_at"))
        if start_ts is None:
            continue
        operation = start.get("event_type", "").strip().lower()
        end_types = (
            {"loading_end"} if operation == "loading_start" else {"unloading_end"}
        )
        end_event = next(
            (
                e
                for e in events
                if e.get("event_type", "").strip().lower() in end_types
            ),
            None,
        )
        if end_event is None:
            continue  # operation still in progress — no fabricated result
        end_ts = _coerce_utc(end_event.get("timestamp") or end_event.get("created_at"))
        if end_ts is None:
            continue
        duration = (end_ts - start_ts).total_seconds()
        if duration < 0:
            continue  # invalid ordering — not a real interval
        timeout = unloading_timeout if "unload" in operation else loading_timeout
        if duration > timeout:
            return RuleResult(
                triggered=True,
                rule="loading.timeout",
                severity=Severity.HIGH,
                message=(
                    f"{operation} exceeded timeout: {duration:.1f}s "
                    f"(limit {timeout:.1f}s)."
                ),
                details={
                    "operation": operation,
                    "duration_s": round(duration, 2),
                    "timeout_s": timeout,
                },
            )

    return RuleResult(
        triggered=False,
        rule="loading.timeout",
        severity=Severity.LOW,
        message="No loading/unloading operation exceeded its timeout.",
        details={"loading_timeout_s": loading_timeout, "unloading_timeout_s": unloading_timeout},
    )


def _timeout(rules: BusinessRulesConfig, key: str, default: float) -> float:
    """Read a numeric timeout from configuration with a safe fallback."""
    raw = rules.get("truck", key, default)
    try:
        parsed = float(raw)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default

