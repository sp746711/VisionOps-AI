"""VisionOps AI — Video Domain Model.

This module defines the internal, framework-free **video** domain model.
It represents how video upload/processing metadata exists internally (as
handled by the video service and persisted via the CSV storage layer) and
is *not* a FastAPI/Pydantic request-response schema and *not* a service.

The model deliberately stays dependency-light:

- It reuses the :class:`~backend.schemas.common.VideoStatus` enum
  instead of redefining statuses.
- It reuses :class:`~backend.exceptions.ValidationError` for invariant
  violations.
- Filename safety, content-type format, and extension allow-listing are
  intentionally *not* duplicated here — those belong to the API schema
  layer (:mod:`backend.schemas.video`).  Only core domain invariants are
  enforced (see :meth:`Video._validate`).

Contents:
    - :class:`Video` — mutable video metadata record.

Usage::

    from backend.models import Video

    video = Video(
        video_id="vid_001",
        filename="warehouse_1.mp4",
        file_size=1048576,
        status="uploaded",
    )
    payload = video.to_dict()
    restored = Video.from_dict(payload)
    video.update(status="processing", processing_started_at="2025-01-01T00:00:00Z")
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime, timezone
from typing import Any

from backend.exceptions import ValidationError
from backend.schemas.common import VideoStatus

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Video:
    """Video upload/processing metadata record (mutable domain object).

    Represents the internally-held metadata for a video through its
    entire lifecycle (``uploaded`` → ``queued`` → ``processing`` →
    ``completed`` / ``failed`` / ``cancelled``).  Instances are
    intentionally **mutable** — the video service transitions status and
    accumulates processing results over time — so ``frozen=True`` is
    deliberately *not* applied.

    The dataclass provides structural equality and a readable ``repr``;
    instances are unhashable because they are mutable.

    Attributes:
        video_id: Unique video identifier (prefix ``vid_`` in the
            service layer).
        filename: Original upload filename.
        file_size: File size in bytes (must be positive).
        content_type: Optional MIME type.
        status: Lifecycle status (one of
            :class:`~backend.schemas.common.VideoStatus`).
        error_message: Optional error description for failed videos.
        created_at: Timezone-aware UTC creation timestamp.
        updated_at: Timezone-aware UTC last-update timestamp.
        processing_started_at: Optional timezone-aware UTC processing
            start timestamp.
        processing_completed_at: Optional timezone-aware UTC processing
            end timestamp.
        duration_seconds: Video duration in seconds (>= 0).
        total_frames: Total frame count (>= 0).
        fps: Frames-per-second (>= 0).
        thumbnail_path: Optional thumbnail file path.
        annotated_path: Optional annotated-video output path.
    """

    video_id: str
    filename: str
    file_size: int
    content_type: str | None = None
    status: VideoStatus = VideoStatus.UPLOADED
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    duration_seconds: float = 0.0
    total_frames: int = 0
    fps: float = 0.0
    thumbnail_path: str | None = None
    annotated_path: str | None = None

    # ------------------------------------------------------------------
    # Construction / Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Normalise status/timestamps and validate core invariants.

        The ``status`` value is coerced into a
        :class:`~backend.schemas.common.VideoStatus` member (matching the
        service layer, which reads raw status strings from CSV).  All
        timestamps are normalised to timezone-aware UTC (naive values are
        assumed to be UTC).  Missing ``created_at`` / ``updated_at`` are
        set to the current UTC time.

        Raises:
            ValidationError: If any core invariant is violated.
        """
        self.status = self._coerce_status(self.status)
        self.created_at = self._coerce_datetime(self.created_at)
        self.updated_at = self._coerce_datetime(self.updated_at)
        self.processing_started_at = self._coerce_datetime(
            self.processing_started_at
        )
        self.processing_completed_at = self._coerce_datetime(
            self.processing_completed_at
        )
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = self.created_at
        self._validate()

    def _validate(self) -> None:
        """Enforce the core domain invariants of a video record.

        Only fundamental invariants are checked here.  Filename safety,
        content-type format, and extension allow-listing are deliberately
        left to the API schema layer to avoid duplicated logic.

        Raises:
            ValidationError: If any invariant is violated.
        """
        if not isinstance(self.video_id, str) or not self.video_id.strip():
            raise ValidationError("Video.video_id must be a non-empty string.")

        if not isinstance(self.filename, str) or not self.filename.strip():
            raise ValidationError(
                "Video.filename must be a non-empty string."
            )

        if not isinstance(self.file_size, int) or self.file_size <= 0:
            raise ValidationError(
                "Video.file_size must be a positive integer, "
                f"got {self.file_size!r}."
            )

        if self.content_type is not None and not isinstance(
            self.content_type, str
        ):
            raise ValidationError(
                "Video.content_type must be a string or None, got "
                f"{type(self.content_type).__name__}."
            )

        if not isinstance(self.status, VideoStatus):
            raise ValidationError(
                "Video.status must be a VideoStatus enum member, got "
                f"{self.status!r}."
            )

        if self.error_message is not None and not isinstance(
            self.error_message, str
        ):
            raise ValidationError(
                "Video.error_message must be a string or None, got "
                f"{type(self.error_message).__name__}."
            )

        if (
            not isinstance(self.duration_seconds, (int, float))
            or float(self.duration_seconds) < 0.0
        ):
            raise ValidationError(
                "Video.duration_seconds must be a non-negative number, "
                f"got {self.duration_seconds!r}."
            )

        if not isinstance(self.total_frames, int) or self.total_frames < 0:
            raise ValidationError(
                "Video.total_frames must be a non-negative integer, "
                f"got {self.total_frames!r}."
            )

        if not isinstance(self.fps, (int, float)) or float(self.fps) < 0.0:
            raise ValidationError(
                "Video.fps must be a non-negative number, "
                f"got {self.fps!r}."
            )

        if self.thumbnail_path is not None and not isinstance(
            self.thumbnail_path, str
        ):
            raise ValidationError(
                "Video.thumbnail_path must be a string or None, got "
                f"{type(self.thumbnail_path).__name__}."
            )

        if self.annotated_path is not None and not isinstance(
            self.annotated_path, str
        ):
            raise ValidationError(
                "Video.annotated_path must be a string or None, got "
                f"{type(self.annotated_path).__name__}."
            )

        if self.created_at is None:
            raise ValidationError("Video.created_at must not be None.")

        if self.updated_at is not None and self.updated_at < self.created_at:
            raise ValidationError(
                "Video.updated_at must not be earlier than created_at."
            )

        if (
            self.processing_started_at is not None
            and self.processing_started_at < self.created_at
        ):
            raise ValidationError(
                "Video.processing_started_at must not be earlier than "
                "created_at."
            )

        if (
            self.processing_completed_at is not None
            and self.processing_started_at is not None
            and self.processing_completed_at < self.processing_started_at
        ):
            raise ValidationError(
                "Video.processing_completed_at must not be earlier than "
                "processing_started_at."
            )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the video record to a plain dictionary.

        Enum values are serialised to their string values and datetime
        fields to ISO 8601 strings so the output is JSON/CSV friendly.

        Returns:
            Dictionary mapping every field name to its value.
        """
        data: dict[str, Any] = {}
        for field_info in fields(self):
            value = getattr(self, field_info.name)
            if isinstance(value, VideoStatus):
                value = value.value
            elif isinstance(value, datetime):
                value = value.isoformat()
            data[field_info.name] = value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Video":
        """Build a :class:`Video` instance from a plain dictionary.

        Unknown keys are ignored, keeping the helper tolerant of
        storage-layer records that may carry extra fields.  The ``status``
        value is coerced into a
        :class:`~backend.schemas.common.VideoStatus` member and all
        timestamps are parsed from ISO 8601 strings and normalised to
        timezone-aware UTC.

        Args:
            data: Dictionary of video record values.

        Returns:
            A new :class:`Video` instance.

        Raises:
            ValidationError: If ``status`` is invalid, a timestamp is
                malformed, or a core invariant is violated.
        """
        known = {field_info.name for field_info in fields(cls)}
        kwargs: dict[str, Any] = {}
        for key, value in data.items():
            if key not in known:
                continue
            kwargs[key] = value

        if "status" in kwargs:
            kwargs["status"] = cls._coerce_status(kwargs["status"])

        for key in (
            "created_at",
            "updated_at",
            "processing_started_at",
            "processing_completed_at",
        ):
            if key in kwargs:
                kwargs[key] = cls._coerce_datetime(kwargs[key])

        return cls(**kwargs)

    # ------------------------------------------------------------------
    # Copy / Update
    # ------------------------------------------------------------------

    def copy(self) -> "Video":
        """Return a shallow copy of this video record.

        The copy is re-validated on construction via
        :meth:`__post_init__`.

        Returns:
            A new :class:`Video` instance with the same field values.
        """
        return replace(self)

    def update(self, **kwargs: Any) -> "Video":
        """Apply field updates to this video record in place.

        Only declared fields may be updated; unknown field names raise
        :class:`~backend.exceptions.ValidationError`.  The ``status``
        value is coerced into a
        :class:`~backend.schemas.common.VideoStatus` member and all
        timestamps are normalised to timezone-aware UTC.  Core domain
        invariants are re-validated after the updates are applied.

        Args:
            **kwargs: Field name/value pairs to apply.

        Returns:
            ``self`` to allow method chaining.

        Raises:
            ValidationError: If an unknown field is supplied, ``status``
                is invalid, or a core invariant is violated after the
                update.
        """
        known = {field_info.name for field_info in fields(self)}
        unknown = sorted(set(kwargs) - known)
        if unknown:
            raise ValidationError(
                f"Unknown video field(s): {', '.join(unknown)}."
            )

        if "status" in kwargs:
            kwargs["status"] = self._coerce_status(kwargs["status"])

        for key in (
            "created_at",
            "updated_at",
            "processing_started_at",
            "processing_completed_at",
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
    def _coerce_status(value: str | VideoStatus) -> VideoStatus:
        """Coerce a raw status value into a :class:`VideoStatus` member.

        Args:
            value: Raw status value (enum member or string).

        Returns:
            The corresponding :class:`VideoStatus` member.

        Raises:
            ValidationError: If *value* is not a valid video status.
        """
        if isinstance(value, VideoStatus):
            return value
        try:
            return VideoStatus(value.strip().lower())
        except (AttributeError, ValueError) as exc:
            valid = ", ".join(sorted(s.value for s in VideoStatus))
            raise ValidationError(
                f"Invalid status {value!r}. Valid statuses: {valid}."
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

__all__ = ["Video"]

