"""VisionOps AI — Detection Domain Model.

This module defines the internal, framework-free **detection** domain
model.  It represents a single object-detection result as produced by the
AI pipeline and persisted via the CSV storage layer.  It is *not* a
FastAPI/Pydantic request-response schema and *not* a service.

The model deliberately stays dependency-light:

- It reuses the :class:`~backend.schemas.common.DetectionClass` enum and
  the :class:`~backend.schemas.common.BoundingBox` value object instead
  of redefining them.
- It reuses :class:`~backend.exceptions.ValidationError` for invariant
  violations.
- Detailed class-name and confidence validation belongs to the analysis
  service/schema layer; only core domain invariants are enforced here
  (see :meth:`Detection._validate`).

Because a detection result is an immutable fact produced by the pipeline,
this model is declared with ``frozen=True``.  Instances are therefore
**hashable** and safe to share across threads/collections without
accidental mutation.

Contents:
    - :class:`Detection` — immutable detection result record.

Usage::

    from backend.models import Detection

    det = Detection(
        detection_id="det_001",
        video_id="vid_001",
        frame_number=12,
        class_name="person",
        confidence=0.95,
        bbox={"x": 10.0, "y": 20.0, "width": 50.0, "height": 100.0},
    )
    payload = det.to_dict()
    restored = Detection.from_dict(payload)
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime, timezone
from typing import Any

from backend.exceptions import ValidationError
from backend.schemas.common import BoundingBox, DetectionClass

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class Detection:
    """A single detection result (immutable domain object).

    Represents one validated object detection produced by the AI
    pipeline.  Instances are immutable: the detection fact itself never
    changes after it is recorded.  As a frozen dataclass it provides
    structural equality, a readable ``repr``, and value-based hashing.

    Attributes:
        detection_id: Unique detection identifier (prefix ``det_`` in the
            service layer).
        video_id: Video the detection belongs to (prefix ``vid_`` in the
            service layer).
        frame_number: Zero-based frame index where the object was
            detected (>= 0).
        class_name: Detected object class
            (:class:`~backend.schemas.common.DetectionClass`).
        confidence: Detection confidence score in ``[0.0, 1.0]``.
        bbox: Normalized bounding box
            (:class:`~backend.schemas.common.BoundingBox`).
        track_id: Optional object tracking identifier.
        created_at: Timezone-aware UTC creation timestamp.
    """

    detection_id: str
    video_id: str
    frame_number: int
    class_name: DetectionClass
    confidence: float
    bbox: BoundingBox
    track_id: str | None = None
    created_at: datetime | None = None

    # ------------------------------------------------------------------
    # Hashing
    # ------------------------------------------------------------------

    def __hash__(self) -> int:
        """Return a stable hash for this immutable detection record.

        The ``bbox`` field is a Pydantic
        :class:`~backend.schemas.common.BoundingBox` value object, which
        is not hashable by default.  Because the dataclass is frozen, a
        custom hash can be safely derived from the immutable serialized
        representation of the record.

        Returns:
            An integer hash consistent with structural equality.
        """
        return hash(
            (
                self.detection_id,
                self.video_id,
                self.frame_number,
                self.class_name.value,
                self.confidence,
                tuple(self.bbox.as_list()),
                self.track_id,
                self.created_at,
            )
        )

    # ------------------------------------------------------------------
    # Construction / Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Normalise class/timestamp and validate core invariants.

        The ``class_name`` value is coerced into a
        :class:`~backend.schemas.common.DetectionClass` member (matching
        the schema layer, which accepts raw class strings).  The
        ``created_at`` timestamp is normalised to timezone-aware UTC
        (naive values are assumed to be UTC); a missing value is set to
        the current UTC time.

        Raises:
            ValidationError: If any core invariant is violated.
        """
        # ``frozen=True`` prevents attribute assignment, so we must use
        # ``object.__setattr__`` to normalise values during init.
        object.__setattr__(self, "class_name", self._coerce_class(self.class_name))
        object.__setattr__(self, "bbox", self._coerce_bbox(self.bbox))
        object.__setattr__(self, "created_at", self._coerce_datetime(self.created_at))
        if self.created_at is None:
            object.__setattr__(self, "created_at", datetime.now(timezone.utc))
        self._validate()

    def _validate(self) -> None:
        """Enforce the core domain invariants of a detection record.

        Only fundamental invariants are checked here.  Fine-grained
        class-name allow-listing and confidence filtering belong to the
        analysis service/schema layer.

        Raises:
            ValidationError: If any invariant is violated.
        """
        if not isinstance(self.detection_id, str) or not self.detection_id.strip():
            raise ValidationError(
                "Detection.detection_id must be a non-empty string."
            )

        if not isinstance(self.video_id, str) or not self.video_id.strip():
            raise ValidationError(
                "Detection.video_id must be a non-empty string."
            )

        if not isinstance(self.frame_number, int) or self.frame_number < 0:
            raise ValidationError(
                "Detection.frame_number must be a non-negative integer, "
                f"got {self.frame_number!r}."
            )

        if not isinstance(self.class_name, DetectionClass):
            raise ValidationError(
                "Detection.class_name must be a DetectionClass member, "
                f"got {self.class_name!r}."
            )

        if (
            not isinstance(self.confidence, (int, float))
            or not (0.0 <= float(self.confidence) <= 1.0)
        ):
            raise ValidationError(
                "Detection.confidence must be within [0.0, 1.0], "
                f"got {self.confidence!r}."
            )

        if not isinstance(self.bbox, BoundingBox):
            raise ValidationError(
                "Detection.bbox must be a BoundingBox, got "
                f"{type(self.bbox).__name__}."
            )

        if self.track_id is not None and not isinstance(self.track_id, str):
            raise ValidationError(
                "Detection.track_id must be a string or None, got "
                f"{type(self.track_id).__name__}."
            )

        if self.created_at is None:
            raise ValidationError("Detection.created_at must not be None.")

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the detection record to a plain dictionary.

        The ``class_name`` enum is serialised to its string value, the
        ``bbox`` value object to its own ``as_list()`` representation,
        and ``created_at`` to an ISO 8601 string so the output is
        JSON/CSV friendly (matching the CSV store header convention
        ``bbox_x, bbox_y, bbox_w, bbox_h``).

        Returns:
            Dictionary mapping every field name to its value.
        """
        return {
            "detection_id": self.detection_id,
            "video_id": self.video_id,
            "frame_number": self.frame_number,
            "class_name": self.class_name.value,
            "confidence": self.confidence,
            "bbox": self.bbox.as_list(),
            "track_id": self.track_id,
            "created_at": self.created_at.isoformat()
            if self.created_at is not None
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Detection":
        """Build a :class:`Detection` instance from a plain dictionary.

        Unknown keys are ignored.  The ``class_name`` value is coerced
        into a :class:`~backend.schemas.common.DetectionClass` member and
        ``bbox`` is accepted either as a
        :class:`~backend.schemas.common.BoundingBox`, a positional list
        of four floats, or a ``{x, y, width, height}`` mapping.  The
        ``created_at`` timestamp is parsed from ISO 8601 and normalised
        to timezone-aware UTC.

        Args:
            data: Dictionary of detection record values.

        Returns:
            A new :class:`Detection` instance.

        Raises:
            ValidationError: If ``class_name`` is invalid, ``bbox`` is
                malformed, a timestamp is malformed, or a core invariant
                is violated.
        """
        known = {field_info.name for field_info in fields(cls)}
        kwargs: dict[str, Any] = {}
        for key, value in data.items():
            if key not in known:
                continue
            kwargs[key] = value

        if "class_name" in kwargs:
            kwargs["class_name"] = cls._coerce_class(kwargs["class_name"])

        if "bbox" in kwargs:
            kwargs["bbox"] = cls._coerce_bbox(kwargs["bbox"])

        if "created_at" in kwargs:
            kwargs["created_at"] = cls._coerce_datetime(kwargs["created_at"])

        return cls(**kwargs)

    # ------------------------------------------------------------------
    # Copy / Update
    # ------------------------------------------------------------------

    def copy(self) -> "Detection":
        """Return a copy of this detection record.

        Because the dataclass is frozen, the copy is an independent
        immutable instance with identical field values (re-validated on
        construction via :meth:`__post_init__`).

        Returns:
            A new :class:`Detection` instance with the same field values.
        """
        return replace(self)

    def update(self, **kwargs: Any) -> "Detection":
        """Return a **new** detection record with updated fields.

        Since detections are immutable, ``update`` does *not* mutate
        ``self``; it returns a new :class:`Detection` instance with the
        supplied field changes applied.  Only declared fields may be
        updated.

        Args:
            **kwargs: Field name/value pairs to apply.

        Returns:
            A new :class:`Detection` instance.

        Raises:
            ValidationError: If an unknown field is supplied or a core
                invariant is violated by the new values.
        """
        known = {field_info.name for field_info in fields(self)}
        unknown = sorted(set(kwargs) - known)
        if unknown:
            raise ValidationError(
                f"Unknown detection field(s): {', '.join(unknown)}."
            )

        current = self.to_dict()
        current.update(kwargs)
        return self.from_dict(current)

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_class(value: str | DetectionClass) -> DetectionClass:
        """Coerce a raw class value into a :class:`DetectionClass` member.

        Args:
            value: Raw class value (enum member or string).

        Returns:
            The corresponding :class:`DetectionClass` member.

        Raises:
            ValidationError: If *value* is not a valid detection class.
        """
        if isinstance(value, DetectionClass):
            return value
        try:
            return DetectionClass(value.strip().lower())
        except (AttributeError, ValueError) as exc:
            valid = ", ".join(sorted(c.value for c in DetectionClass))
            raise ValidationError(
                f"Invalid class_name {value!r}. Valid classes: {valid}."
            ) from exc

    @staticmethod
    def _coerce_bbox(value: BoundingBox | list | tuple | dict) -> BoundingBox:
        """Coerce a raw bbox value into a :class:`BoundingBox`.

        Accepts a :class:`BoundingBox` directly, a positional
        ``[x, y, width, height]`` sequence, or a mapping with ``x``,
        ``y``, ``width``, ``height`` keys.

        Args:
            value: Raw bounding-box value.

        Returns:
            A :class:`~backend.schemas.common.BoundingBox`.

        Raises:
            ValidationError: If *value* cannot be interpreted as a
                bounding box.
        """
        if isinstance(value, BoundingBox):
            return value

        if isinstance(value, (list, tuple)):
            if len(value) != 4:
                raise ValidationError(
                    "Detection.bbox sequence must contain exactly 4 "
                    f"values, got {len(value)}."
                )
            try:
                return BoundingBox(
                    x=value[0], y=value[1], width=value[2], height=value[3]
                )
            except ValueError as exc:
                raise ValidationError(
                    f"Invalid Detection.bbox sequence: {exc}"
                ) from exc

        if isinstance(value, dict):
            missing = {"x", "y", "width", "height"} - set(value)
            if missing:
                raise ValidationError(
                    "Detection.bbox dict is missing key(s): "
                    f"{', '.join(sorted(missing))}."
                )
            try:
                return BoundingBox(
                    x=value["x"],
                    y=value["y"],
                    width=value["width"],
                    height=value["height"],
                )
            except ValueError as exc:
                raise ValidationError(
                    f"Invalid Detection.bbox dict: {exc}"
                ) from exc

        raise ValidationError(
            "Detection.bbox must be a BoundingBox, a [x, y, w, h] "
            f"sequence, or a mapping, got {type(value).__name__}."
        )

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

__all__ = ["Detection"]

