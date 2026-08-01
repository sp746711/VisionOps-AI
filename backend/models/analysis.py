"""VisionOps AI — Analysis Domain Model.

This module defines the internal, framework-free **analysis** domain
model.  It represents the aggregate result of a detection-analysis run
over a video — counts, class breakdowns, confidence statistics — as
produced by the analysis service.  It is *not* a FastAPI/Pydantic
request-response schema and *not* a service.

The model deliberately stays dependency-light:

- It reuses :class:`~backend.exceptions.ValidationError` for invariant
  violations.
- Aggregation algorithms, class-name allow-listing, and confidence
  filtering belong to the analysis service/business layer; only core
  domain invariants are enforced here (see :meth:`Analysis._validate`).

An analysis result is an immutable fact computed at a point in time, so
this model is declared with ``frozen=True``.  Instances are therefore
**hashable** and safe to share across collections.

Contents:
    - :class:`Analysis` — immutable analysis-run result record.

Usage::

    from backend.models import Analysis

    analysis = Analysis(
        analysis_id="anl_001",
        video_id="vid_001",
        total_detections=42,
        unique_classes=3,
        average_confidence=0.87,
        class_counts={"person": 20, "forklift": 12, "pallet": 10},
    )
    payload = analysis.to_dict()
    restored = Analysis.from_dict(payload)
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
class Analysis:
    """A single analysis-run result (immutable domain object).

    Represents the aggregate outcome of a detection-analysis run over a
    video.  Instances are immutable — the analysis result never changes
    after it is recorded.  As a frozen dataclass it provides structural
    equality, a readable ``repr``, and value-based hashing.

    Attributes:
        analysis_id: Unique analysis record identifier.
        video_id: The video that was analysed.
        total_detections: Total detection count (>= 0).
        unique_classes: Number of distinct object classes (>= 0).
        average_confidence: Mean confidence score in ``[0.0, 1.0]``.
        class_counts: Per-class detection counts (non-negative).
        created_at: Timezone-aware UTC creation timestamp.
    """

    analysis_id: str
    video_id: str
    total_detections: int = 0
    unique_classes: int = 0
    average_confidence: float = 0.0
    class_counts: dict[str, int] | None = None
    created_at: datetime | None = None

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    def __hash__(self) -> int:
        """Return a stable hash for this immutable analysis record.

        The ``class_counts`` mapping is converted to a sorted tuple of
        items for a stable, order-independent hash.

        Returns:
            An integer hash based on the analysis fields.
        """
        counts = self.class_counts or {}
        return hash(
            (
                self.analysis_id,
                self.video_id,
                self.total_detections,
                self.unique_classes,
                self.average_confidence,
                tuple(sorted(counts.items())),
                self.created_at,
            )
        )

    # ------------------------------------------------------------------
    # Construction / Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Normalise class_counts/timestamp and validate core invariants.

        The ``class_counts`` mapping is copied so the immutable record
        never aliases a caller-supplied mutable dict.  The ``created_at``
        timestamp is normalised to timezone-aware UTC (naive values are
        assumed to be UTC); a missing value is set to the current UTC
        time via :func:`backend.utils.date_utils.now_utc`.

        Raises:
            ValidationError: If any core invariant is violated.
        """
        if self.class_counts is not None:
            object.__setattr__(self, "class_counts", dict(self.class_counts))
        object.__setattr__(self, "created_at", self._coerce_datetime(self.created_at))
        if self.created_at is None:
            object.__setattr__(self, "created_at", now_utc())
        self._validate()

    def _validate(self) -> None:
        """Enforce the core domain invariants of an analysis record.

        Only fundamental invariants are checked here.  Aggregation
        algorithms and class-name allow-listing belong to the analysis
        service/business layer.

        Raises:
            ValidationError: If any invariant is violated.
        """
        if not isinstance(self.analysis_id, str) or not self.analysis_id.strip():
            raise ValidationError(
                "Analysis.analysis_id must be a non-empty string."
            )

        if not isinstance(self.video_id, str) or not self.video_id.strip():
            raise ValidationError(
                "Analysis.video_id must be a non-empty string."
            )

        if not isinstance(self.total_detections, int) or self.total_detections < 0:
            raise ValidationError(
                "Analysis.total_detections must be a non-negative "
                f"integer, got {self.total_detections!r}."
            )

        if not isinstance(self.unique_classes, int) or self.unique_classes < 0:
            raise ValidationError(
                "Analysis.unique_classes must be a non-negative integer, "
                f"got {self.unique_classes!r}."
            )

        if (
            not isinstance(self.average_confidence, (int, float))
            or not (0.0 <= float(self.average_confidence) <= 1.0)
        ):
            raise ValidationError(
                "Analysis.average_confidence must be within [0.0, 1.0], "
                f"got {self.average_confidence!r}."
            )

        if self.class_counts is not None:
            if not isinstance(self.class_counts, dict):
                raise ValidationError(
                    "Analysis.class_counts must be a dict or None, got "
                    f"{type(self.class_counts).__name__}."
                )
            for class_name, count in self.class_counts.items():
                if not isinstance(class_name, str) or not class_name.strip():
                    raise ValidationError(
                        "Analysis.class_counts keys must be non-empty "
                        f"strings, got {class_name!r}."
                    )
                if not isinstance(count, int) or count < 0:
                    raise ValidationError(
                        f"Analysis.class_counts[{class_name!r}] must be a "
                        f"non-negative integer, got {count!r}."
                    )

        if self.created_at is None:
            raise ValidationError("Analysis.created_at must not be None.")

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the analysis record to a plain dictionary.

        The ``created_at`` is serialised to an ISO 8601 string so the
        output is JSON/CSV friendly.

        Returns:
            Dictionary mapping every field name to its value.
        """
        return {
            "analysis_id": self.analysis_id,
            "video_id": self.video_id,
            "total_detections": self.total_detections,
            "unique_classes": self.unique_classes,
            "average_confidence": self.average_confidence,
            "class_counts": dict(self.class_counts)
            if self.class_counts is not None
            else None,
            "created_at": self.created_at.isoformat()
            if self.created_at is not None
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Analysis":
        """Build a :class:`Analysis` instance from a plain dictionary.

        Unknown keys are ignored.  The ``created_at`` is parsed from ISO
        8601 and normalised to timezone-aware UTC.

        Args:
            data: Dictionary of analysis record values.

        Returns:
            A new :class:`Analysis` instance.

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

        if "created_at" in kwargs:
            kwargs["created_at"] = cls._coerce_datetime(kwargs["created_at"])

        return cls(**kwargs)

    # ------------------------------------------------------------------
    # Copy / Update
    # ------------------------------------------------------------------

    def copy(self) -> "Analysis":
        """Return a copy of this analysis record.

        Because the dataclass is frozen, the copy is an independent
        immutable instance with identical field values (re-validated on
        construction via :meth:`__post_init__`).

        Returns:
            A new :class:`Analysis` instance with the same field values.
        """
        return replace(self)

    def update(self, **kwargs: Any) -> "Analysis":
        """Return a **new** analysis record with updated fields.

        Since analysis records are immutable, ``update`` does *not*
        mutate ``self``; it returns a new :class:`Analysis` instance with
        the supplied field changes applied.  Only declared fields may be
        updated.

        Args:
            **kwargs: Field name/value pairs to apply.

        Returns:
            A new :class:`Analysis` instance.

        Raises:
            ValidationError: If an unknown field is supplied or a core
                invariant is violated by the new values.
        """
        known = {field_info.name for field_info in fields(self)}
        unknown = sorted(set(kwargs) - known)
        if unknown:
            raise ValidationError(
                f"Unknown analysis field(s): {', '.join(unknown)}."
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

__all__ = ["Analysis"]

