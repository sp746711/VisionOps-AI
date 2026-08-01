"""VisionOps AI — KPI Domain Model.

This module defines the internal, framework-free **KPI** domain model.
It represents a single key-performance-indicator measurement computed by
the KPI engine and persisted via the CSV storage layer.  It is *not* a
FastAPI/Pydantic request-response schema and *not* a service.

The model deliberately stays dependency-light:

- It reuses :class:`~backend.exceptions.ValidationError` for invariant
  violations and :mod:`backend.utils.date_utils` / :mod:`backend.utils.id_generator`
  for timestamp/identifier handling.
- KPI computation and aggregation rules belong to the KPI engine/service
  layer; only core domain invariants are enforced here (see
  :meth:`KPI._validate`).

A KPI measurement is an immutable fact computed at a point in time, so
this model is declared with ``frozen=True``.  Instances are therefore
**hashable** and safe to share across collections.

Contents:
    - :class:`KPI` — immutable KPI measurement record.

Usage::

    from backend.models import KPI

    kpi = KPI(
        kpi_id="kpi_001",
        metric="spoilage_risk_index",
        value=0.34,
        unit="index",
        video_id="vid_001",
    )
    payload = kpi.to_dict()
    restored = KPI.from_dict(payload)
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime, timezone
from typing import Any

from backend.exceptions import ValidationError
from backend.utils.date_utils import now_utc

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class KPI:
    """A single KPI measurement (immutable domain object).

    Represents one computed key-performance-indicator value.  Instances
    are immutable — the measurement fact never changes after it is
    recorded.  As a frozen dataclass it provides structural equality, a
    readable ``repr``, and value-based hashing.

    Attributes:
        kpi_id: Unique KPI record identifier.
        metric: KPI metric name (e.g. ``"spoilage_risk_index"``,
            ``"freshness_score"``).
        value: Numeric value of the metric.
        unit: Optional unit label (e.g. ``"index"``, ``"percent"``,
            ``"count"``).
        video_id: Optional video the KPI is scoped to.
        timestamp: Timezone-aware UTC computation timestamp.
    """

    kpi_id: str
    metric: str
    value: float
    unit: str | None = None
    video_id: str | None = None
    timestamp: datetime | None = None

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    def __hash__(self) -> int:
        """Return a stable hash for this immutable KPI record.

        A custom hash is provided for consistency with structural
        equality (the dataclass auto-generates ``__eq__``).

        Returns:
            An integer hash based on the KPI fields.
        """
        return hash(
            (
                self.kpi_id,
                self.metric,
                self.value,
                self.unit,
                self.video_id,
                self.timestamp,
            )
        )

    # ------------------------------------------------------------------
    # Construction / Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Normalise timestamp and validate core invariants.

        The ``timestamp`` value is normalised to timezone-aware UTC
        (naive values are assumed to be UTC); a missing value is set to
        the current UTC time via
        :func:`backend.utils.date_utils.now_utc`.

        Raises:
            ValidationError: If any core invariant is violated.
        """
        object.__setattr__(self, "timestamp", self._coerce_datetime(self.timestamp))
        if self.timestamp is None:
            object.__setattr__(self, "timestamp", now_utc())
        self._validate()

    def _validate(self) -> None:
        """Enforce the core domain invariants of a KPI record.

        Only fundamental invariants are checked here.  Metric-name
        allow-listing and value-range semantics for specific metrics
        belong to the KPI engine/service layer.

        Raises:
            ValidationError: If any invariant is violated.
        """
        if not isinstance(self.kpi_id, str) or not self.kpi_id.strip():
            raise ValidationError("KPI.kpi_id must be a non-empty string.")

        if not isinstance(self.metric, str) or not self.metric.strip():
            raise ValidationError("KPI.metric must be a non-empty string.")

        if not isinstance(self.value, (int, float)):
            raise ValidationError(
                "KPI.value must be a number, got "
                f"{type(self.value).__name__}."
            )

        if self.unit is not None and not isinstance(self.unit, str):
            raise ValidationError(
                "KPI.unit must be a string or None, got "
                f"{type(self.unit).__name__}."
            )

        if self.video_id is not None and not isinstance(self.video_id, str):
            raise ValidationError(
                "KPI.video_id must be a string or None, got "
                f"{type(self.video_id).__name__}."
            )

        if self.timestamp is None:
            raise ValidationError("KPI.timestamp must not be None.")

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the KPI record to a plain dictionary.

        The ``timestamp`` is serialised to an ISO 8601 string so the
        output is JSON/CSV friendly (matching the CSV store header
        convention).

        Returns:
            Dictionary mapping every field name to its value.
        """
        return {
            "kpi_id": self.kpi_id,
            "video_id": self.video_id,
            "metric": self.metric,
            "value": self.value,
            "unit": self.unit,
            "timestamp": self.timestamp.isoformat()
            if self.timestamp is not None
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "KPI":
        """Build a :class:`KPI` instance from a plain dictionary.

        Unknown keys are ignored.  The ``timestamp`` is parsed from ISO
        8601 and normalised to timezone-aware UTC.

        Args:
            data: Dictionary of KPI record values.

        Returns:
            A new :class:`KPI` instance.

        Raises:
            ValidationError: If a timestamp is malformed or a core
                invariant is violated.
        """
        known = {field_info.name for field_info in fields(cls)}
        kwargs: dict[str, Any] = {}
        for key, value in data.items():
            if key not in known:
                continue
            kwargs[key] = value

        if "timestamp" in kwargs:
            kwargs["timestamp"] = cls._coerce_datetime(kwargs["timestamp"])

        return cls(**kwargs)

    # ------------------------------------------------------------------
    # Copy / Update
    # ------------------------------------------------------------------

    def copy(self) -> "KPI":
        """Return a copy of this KPI record.

        Because the dataclass is frozen, the copy is an independent
        immutable instance with identical field values (re-validated on
        construction via :meth:`__post_init__`).

        Returns:
            A new :class:`KPI` instance with the same field values.
        """
        return replace(self)

    def update(self, **kwargs: Any) -> "KPI":
        """Return a **new** KPI record with updated fields.

        Since KPIs are immutable, ``update`` does *not* mutate ``self``;
        it returns a new :class:`KPI` instance with the supplied field
        changes applied.  Only declared fields may be updated.

        Args:
            **kwargs: Field name/value pairs to apply.

        Returns:
            A new :class:`KPI` instance.

        Raises:
            ValidationError: If an unknown field is supplied or a core
                invariant is violated by the new values.
        """
        known = {field_info.name for field_info in fields(self)}
        unknown = sorted(set(kwargs) - known)
        if unknown:
            raise ValidationError(
                f"Unknown KPI field(s): {', '.join(unknown)}."
            )

        current = self.to_dict()
        current.update(kwargs)
        return self.from_dict(current)

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

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

__all__ = ["KPI"]

