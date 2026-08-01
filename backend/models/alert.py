"""VisionOps AI — Alert Domain Model.

This module defines the internal, framework-free **alert** domain model.
It represents an alert record raised by the monitoring/alert engine and
persisted via the CSV storage layer.  It is *not* a FastAPI/Pydantic
request-response schema and *not* a service.

The model deliberately stays dependency-light:

- It reuses the :class:`~backend.schemas.common.Severity` enum instead
  of redefining severity levels.
- It reuses :class:`~backend.exceptions.ValidationError` for invariant
  violations.
- Alert-raising rules, escalation logic, and notification dispatch belong
  to the alert engine/service layer; only core domain invariants are
  enforced here (see :meth:`Alert._validate`).

Alerts are **mutable** records: they transition through a lifecycle
(raised → acknowledged → escalated) and are updated in place by the
service layer.  Instances are therefore intentionally not frozen and not
hashable.

Contents:
    - :class:`Alert` — mutable alert record.

Usage::

    from backend.models import Alert

    alert = Alert(
        alert_id="alr_001",
        video_id="vid_001",
        severity="high",
        message="Elevated spoilage risk detected.",
        source="analytics",
    )
    alert.acknowledge(by="operator_1")
    payload = alert.to_dict()
    restored = Alert.from_dict(payload)
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


@dataclass(slots=True)
class Alert:
    """An alert record (mutable domain object).

    Represents one alert raised by the monitoring system.  Instances are
    intentionally **mutable** so the service layer can acknowledge and
    escalate alerts over their lifecycle.  The dataclass provides
    structural equality and a readable ``repr``; instances are unhashable
    because they are mutable.

    Attributes:
        alert_id: Unique alert identifier.
        severity: Alert severity
            (:class:`~backend.schemas.common.Severity`).
        message: Human-readable alert message.
        video_id: Optional video the alert is associated with.
        acknowledged: Whether the alert has been acknowledged.
        acknowledged_at: Optional timezone-aware UTC acknowledgement
            timestamp.
        acknowledged_by: Optional user that acknowledged the alert.
        escalated: Whether the alert has been escalated.
        escalation_level: Optional escalation level (>= 1).
        source: Optional source of the alert (e.g. ``"analytics"``,
            ``"ai"``).
        created_at: Timezone-aware UTC creation timestamp.
        updated_at: Timezone-aware UTC last-update timestamp.
    """

    alert_id: str
    message: str
    severity: Severity = Severity.MEDIUM
    video_id: str | None = None
    acknowledged: bool = False
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    escalated: bool = False
    escalation_level: int | None = None
    source: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # ------------------------------------------------------------------
    # Construction / Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Normalise severity/timestamps and validate core invariants.

        The ``severity`` value is coerced into a
        :class:`~backend.schemas.common.Severity` member (matching the
        schema layer, which accepts raw severity strings).  All
        timestamps are normalised to timezone-aware UTC (naive values are
        assumed to be UTC).  Missing ``created_at`` / ``updated_at`` are
        set to the current UTC time.

        Raises:
            ValidationError: If any core invariant is violated.
        """
        self.severity = self._coerce_severity(self.severity)
        self.created_at = self._coerce_datetime(self.created_at)
        self.updated_at = self._coerce_datetime(self.updated_at)
        self.acknowledged_at = self._coerce_datetime(self.acknowledged_at)
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = self.created_at
        self._validate()

    def _validate(self) -> None:
        """Enforce the core domain invariants of an alert record.

        Only fundamental invariants are checked here.  Alert-raising
        rules, escalation policy, and notification dispatch belong to the
        alert engine/service layer.

        Raises:
            ValidationError: If any invariant is violated.
        """
        if not isinstance(self.alert_id, str) or not self.alert_id.strip():
            raise ValidationError("Alert.alert_id must be a non-empty string.")

        if not isinstance(self.message, str) or not self.message.strip():
            raise ValidationError("Alert.message must be a non-empty string.")

        if not isinstance(self.severity, Severity):
            raise ValidationError(
                "Alert.severity must be a Severity member, got "
                f"{self.severity!r}."
            )

        if self.video_id is not None and not isinstance(self.video_id, str):
            raise ValidationError(
                "Alert.video_id must be a string or None, got "
                f"{type(self.video_id).__name__}."
            )

        if not isinstance(self.acknowledged, bool):
            raise ValidationError(
                "Alert.acknowledged must be a bool, got "
                f"{type(self.acknowledged).__name__}."
            )

        if self.acknowledged_by is not None and not isinstance(
            self.acknowledged_by, str
        ):
            raise ValidationError(
                "Alert.acknowledged_by must be a string or None, got "
                f"{type(self.acknowledged_by).__name__}."
            )

        if not isinstance(self.escalated, bool):
            raise ValidationError(
                "Alert.escalated must be a bool, got "
                f"{type(self.escalated).__name__}."
            )

        if self.escalation_level is not None and (
            not isinstance(self.escalation_level, int)
            or self.escalation_level < 1
        ):
            raise ValidationError(
                "Alert.escalation_level must be a positive integer or "
                f"None, got {self.escalation_level!r}."
            )

        if self.source is not None and not isinstance(self.source, str):
            raise ValidationError(
                "Alert.source must be a string or None, got "
                f"{type(self.source).__name__}."
            )

        if self.created_at is None:
            raise ValidationError("Alert.created_at must not be None.")

        if self.updated_at is not None and self.updated_at < self.created_at:
            raise ValidationError(
                "Alert.updated_at must not be earlier than created_at."
            )

        if self.acknowledged_at is not None and (
            self.created_at is not None
            and self.acknowledged_at < self.created_at
        ):
            raise ValidationError(
                "Alert.acknowledged_at must not be earlier than created_at."
            )

        if self.acknowledged and self.acknowledged_at is None:
            raise ValidationError(
                "Alert.acknowledged is True but acknowledged_at is None."
            )

        if self.acknowledged and self.acknowledged_by is None:
            raise ValidationError(
                "Alert.acknowledged is True but acknowledged_by is None."
            )

    # ------------------------------------------------------------------
    # Lifecycle Helpers
    # ------------------------------------------------------------------

    def acknowledge(self, by: str) -> "Alert":
        """Mark this alert as acknowledged by the given user.

        The ``acknowledged`` flag is set to ``True`` and both
        ``acknowledged_at`` and ``updated_at`` are set to the current UTC
        time.

        Args:
            by: Username/identifier of the user acknowledging the alert.

        Returns:
            ``self`` to allow method chaining.

        Raises:
            ValidationError: If *by* is empty.
        """
        if not isinstance(by, str) or not by.strip():
            raise ValidationError(
                "Acknowledging user ('by') must be a non-empty string."
            )
        now = datetime.now(timezone.utc)
        self.acknowledged = True
        self.acknowledged_at = now
        self.acknowledged_by = by.strip()
        self.updated_at = now
        self._validate()
        return self

    def escalate(self, level: int | None = None) -> "Alert":
        """Escalate this alert, optionally to a specific level.

        The ``escalated`` flag is set to ``True``; if *level* is provided
        it is set as ``escalation_level`` (otherwise the level is
        incremented from its current value, starting at ``1``).
        ``updated_at`` is set to the current UTC time.

        Args:
            level: Optional explicit escalation level (>= 1).

        Returns:
            ``self`` to allow method chaining.

        Raises:
            ValidationError: If *level* is not a positive integer.
        """
        if level is None:
            level = (self.escalation_level or 0) + 1
        if not isinstance(level, int) or level < 1:
            raise ValidationError(
                f"Escalation level must be a positive integer, got {level!r}."
            )
        self.escalated = True
        self.escalation_level = level
        self.updated_at = datetime.now(timezone.utc)
        self._validate()
        return self

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the alert record to a plain dictionary.

        The ``severity`` enum is serialised to its string value and all
        timestamps to ISO 8601 strings so the output is JSON/CSV
        friendly (matching the CSV store header convention).

        Returns:
            Dictionary mapping every field name to its value.
        """
        data: dict[str, Any] = {}
        for field_info in fields(self):
            value = getattr(self, field_info.name)
            if isinstance(value, Severity):
                value = value.value
            elif isinstance(value, datetime):
                value = value.isoformat()
            data[field_info.name] = value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Alert":
        """Build a :class:`Alert` instance from a plain dictionary.

        Unknown keys are ignored.  The ``severity`` value is coerced into
        a :class:`~backend.schemas.common.Severity` member and all
        timestamps are parsed from ISO 8601 and normalised to
        timezone-aware UTC.

        Args:
            data: Dictionary of alert record values.

        Returns:
            A new :class:`Alert` instance.

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

        for key in (
            "created_at",
            "updated_at",
            "acknowledged_at",
        ):
            if key in kwargs:
                kwargs[key] = cls._coerce_datetime(kwargs[key])

        return cls(**kwargs)

    # ------------------------------------------------------------------
    # Copy / Update
    # ------------------------------------------------------------------

    def copy(self) -> "Alert":
        """Return a shallow copy of this alert record.

        The copy is re-validated on construction via
        :meth:`__post_init__`.

        Returns:
            A new :class:`Alert` instance with the same field values.
        """
        return replace(self)

    def update(self, **kwargs: Any) -> "Alert":
        """Apply field updates to this alert record in place.

        Only declared fields may be updated; unknown field names raise
        :class:`~backend.exceptions.ValidationError`.  The ``severity``
        value is coerced into a :class:`~backend.schemas.common.Severity`
        member and all timestamps are normalised to timezone-aware UTC.
        Core domain invariants are re-validated after the updates are
        applied.

        Args:
            **kwargs: Field name/value pairs to apply.

        Returns:
            ``self`` to allow method chaining.

        Raises:
            ValidationError: If an unknown field is supplied, ``severity``
                is invalid, or a core invariant is violated after the
                update.
        """
        known = {field_info.name for field_info in fields(self)}
        unknown = sorted(set(kwargs) - known)
        if unknown:
            raise ValidationError(
                f"Unknown alert field(s): {', '.join(unknown)}."
            )

        if "severity" in kwargs:
            kwargs["severity"] = self._coerce_severity(kwargs["severity"])

        for key in (
            "created_at",
            "updated_at",
            "acknowledged_at",
        ):
            if key in kwargs:
                kwargs[key] = self._coerce_datetime(kwargs[key])

        for key, value in kwargs.items():
            setattr(self, key, value)

        self._validate()
        return self

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

__all__ = ["Alert"]

