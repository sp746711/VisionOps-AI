"""VisionOps AI — Event Domain Model.

This module defines the internal, framework-free **event** domain model.
It represents a business event (a noteworthy occurrence detected by the
monitoring pipeline) as persisted via the CSV storage layer.  It is *not*
a FastAPI/Pydantic request-response schema and *not* a service.

The model deliberately stays dependency-light:

- It reuses the :class:`~backend.schemas.common.Severity` enum instead
  of redefining severity levels.
- It reuses :class:`~backend.exceptions.ValidationError` for invariant
  violations.
- Event-type allow-listing and business semantics belong to the event
  engine/service layer; only core domain invariants are enforced here
  (see :meth:`Event._validate`).

Events are immutable facts recorded at a point in time, so this model is
declared with ``frozen=True``.  Instances are therefore **hashable** and
safe to share across collections.

Contents:
    - :class:`Event` — immutable business-event record.

Usage::

    from backend.models import Event

    event = Event(
        event_id="evt_001",
        video_id="vid_001",
        event_type="spoilage_risk",
        description="Elevated temperature detected.",
        severity="high",
        source="analytics",
    )
    payload = event.to_dict()
    restored = Event.from_dict(payload)
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime, timezone
from typing import Any

from backend.exceptions import ValidationError
from backend.schemas.common import Severity

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class Event:
    """A single business event (immutable domain object).

    Represents one recorded business event such as a spoilage risk, an
    inventory movement, or an anomaly detected during monitoring.
    Instances are immutable — the event fact never changes after it is
    recorded.  As a frozen dataclass it provides structural equality, a
    readable ``repr``, and value-based hashing.

    Attributes:
        event_id: Unique event identifier.
        video_id: Optional video the event is associated with.
        event_type: Machine-readable event type (e.g.
            ``"spoilage_risk"``, ``"temperature_breach"``).
        description: Optional human-readable description.
        severity: Event severity
            (:class:`~backend.schemas.common.Severity`).
        source: Optional source of the event (e.g. ``"analytics"``,
            ``"ai"``).
        created_at: Timezone-aware UTC creation timestamp.
        updated_at: Optional timezone-aware UTC last-update timestamp.
    """

    event_id: str
    event_type: str
    severity: Severity = Severity.LOW
    description: str | None = None
    video_id: str | None = None
    source: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    def __hash__(self) -> int:
        """Return a stable hash for this immutable event record.

        A custom hash is provided for consistency with structural
        equality (the dataclass auto-generates ``__eq__``).

        Returns:
            An integer hash based on the event fields.
        """
        return hash(
            (
                self.event_id,
                self.event_type,
                self.severity.value,
                self.description,
                self.video_id,
                self.source,
                self.created_at,
                self.updated_at,
            )
        )

    # ------------------------------------------------------------------
    # Construction / Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Normalise severity/timestamps and validate core invariants.

        The ``severity`` value is coerced into a
        :class:`~backend.schemas.common.Severity` member (matching the
        schema layer, which accepts raw severity strings).  All
        timestamps are normalised to timezone-aware UTC (naive values are
        assumed to be UTC); a missing ``created_at`` is set to the
        current UTC time.

        Raises:
            ValidationError: If any core invariant is violated.
        """
        object.__setattr__(self, "severity", self._coerce_severity(self.severity))
        object.__setattr__(self, "created_at", self._coerce_datetime(self.created_at))
        object.__setattr__(self, "updated_at", self._coerce_datetime(self.updated_at))
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.now(timezone.utc))
        self._validate()

    def _validate(self) -> None:
        """Enforce the core domain invariants of an event record.

        Only fundamental invariants are checked here.  Event-type
        allow-listing and domain semantics belong to the event
        engine/service layer.

        Raises:
            ValidationError: If any invariant is violated.
        """
        if not isinstance(self.event_id, str) or not self.event_id.strip():
            raise ValidationError("Event.event_id must be a non-empty string.")

        if not isinstance(self.event_type, str) or not self.event_type.strip():
            raise ValidationError(
                "Event.event_type must be a non-empty string."
            )

        if not isinstance(self.severity, Severity):
            raise ValidationError(
                "Event.severity must be a Severity member, got "
                f"{self.severity!r}."
            )

        if self.description is not None and not isinstance(
            self.description, str
        ):
            raise ValidationError(
                "Event.description must be a string or None, got "
                f"{type(self.description).__name__}."
            )

        if self.video_id is not None and not isinstance(self.video_id, str):
            raise ValidationError(
                "Event.video_id must be a string or None, got "
                f"{type(self.video_id).__name__}."
            )

        if self.source is not None and not isinstance(self.source, str):
            raise ValidationError(
                "Event.source must be a string or None, got "
                f"{type(self.source).__name__}."
            )

        if self.created_at is None:
            raise ValidationError("Event.created_at must not be None.")

        if self.updated_at is not None and self.updated_at < self.created_at:
            raise ValidationError(
                "Event.updated_at must not be earlier than created_at."
            )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the event record to a plain dictionary.

        The ``severity`` enum is serialised to its string value and all
        timestamps to ISO 8601 strings so the output is JSON/CSV
        friendly (matching the CSV store header convention).

        Returns:
            Dictionary mapping every field name to its value.
        """
        return {
            "event_id": self.event_id,
            "video_id": self.video_id,
            "event_type": self.event_type,
            "description": self.description,
            "severity": self.severity.value,
            "source": self.source,
            "created_at": self.created_at.isoformat()
            if self.created_at is not None
            else None,
            "updated_at": self.updated_at.isoformat()
            if self.updated_at is not None
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        """Build a :class:`Event` instance from a plain dictionary.

        Unknown keys are ignored.  The ``severity`` value is coerced into
        a :class:`~backend.schemas.common.Severity` member and all
        timestamps are parsed from ISO 8601 and normalised to
        timezone-aware UTC.

        Args:
            data: Dictionary of event record values.

        Returns:
            A new :class:`Event` instance.

        Raises:
            ValidationError: If ``severity`` is invalid, a timestamp is
                malformed, or a core invariant is violated.
        """
        known = {field_info.name for field_info in fields(cls)}
        kwargs: dict[str, Any] = {}
        for key, value in data.items():
            if key not in known:
                continue
            kwargs[key] = value

        if "severity" in kwargs:
            kwargs["severity"] = cls._coerce_severity(kwargs["severity"])

        for key in ("created_at", "updated_at"):
            if key in kwargs:
                kwargs[key] = cls._coerce_datetime(kwargs[key])

        return cls(**kwargs)

    # ------------------------------------------------------------------
    # Copy / Update
    # ------------------------------------------------------------------

    def copy(self) -> "Event":
        """Return a copy of this event record.

        Because the dataclass is frozen, the copy is an independent
        immutable instance with identical field values (re-validated on
        construction via :meth:`__post_init__`).

        Returns:
            A new :class:`Event` instance with the same field values.
        """
        return replace(self)

    def update(self, **kwargs: Any) -> "Event":
        """Return a **new** event record with updated fields.

        Since events are immutable, ``update`` does *not* mutate
        ``self``; it returns a new :class:`Event` instance with the
        supplied field changes applied.  Only declared fields may be
        updated.

        Args:
            **kwargs: Field name/value pairs to apply.

        Returns:
            A new :class:`Event` instance.

        Raises:
            ValidationError: If an unknown field is supplied or a core
                invariant is violated by the new values.
        """
        known = {field_info.name for field_info in fields(self)}
        unknown = sorted(set(kwargs) - known)
        if unknown:
            raise ValidationError(
                f"Unknown event field(s): {', '.join(unknown)}."
            )

        current = self.to_dict()
        current.update(kwargs)
        return self.from_dict(current)

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_severity(value: str | Severity) -> Severity:
        """Coerce a raw severity value into a :class:`Severity` member.

        Args:
            value: Raw severity value (enum member or string).

        Returns:
            The corresponding :class:`Severity` member.

        Raises:
            ValidationError: If *value* is not a valid severity level.
        """
        if isinstance(value, Severity):
            return value
        try:
            return Severity(value.strip().lower())
        except (AttributeError, ValueError) as exc:
            valid = ", ".join(sorted(s.value for s in Severity))
            raise ValidationError(
                f"Invalid severity {value!r}. Valid severities: {valid}."
            ) from exc

    @staticmethod
    def _coerce_datetime(value: datetime | str | None) -> datetime | None:
        """Normalise a datetime-like value to timezone-aware UTC.

        Args:
            value: Raw timestamp (``datetime``, ISO-8601 string, or
                ``None``).

        Returns:
            Timezone-aware UTC datetime, or ``None``.

        Raises:
            ValidationError: If *value* is not a datetime, string, or
                ``None``, or if the string is not a valid ISO-8601
                timestamp.
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValidationError(
                    f"Invalid ISO-8601 timestamp: {value!r}."
                ) from exc
        else:
            raise ValidationError(
                "Timestamp must be a datetime, ISO-8601 string, or None, "
                f"got {type(value).__name__}."
            )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["Event"]

