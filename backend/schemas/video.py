"""VisionOps AI — Video Domain Schemas.

Pydantic v2 schemas for the video upload, metadata, and processing
domains. These map directly to the interfaces exposed by
:mod:`backend.services.video_service` and the videos API endpoints.

Contents:
    - :class:`VideoUploadRequest` — request body for initiating an upload.
    - :class:`UploadRequest` — alias of :class:`VideoUploadRequest`
      (compat with existing test suite).
    - :class:`VideoMetadata` — full video metadata record.
    - :class:`VideoResponse` — video metadata returned to clients.
    - :class:`VideoProcessingRequest` — request body for processing a video.
    - :class:`VideoStatus` — video lifecycle status enum
      (re-exported from :mod:`backend.schemas.common`).

Validation covers required fields, filename safety, video file
extensions, positive file sizes, content types, UUID identifiers, and
status enumeration.

Usage:
    from backend.schemas.video import (
        VideoUploadRequest, UploadRequest, VideoMetadata, VideoResponse,
        VideoProcessingRequest, VideoStatus,
    )
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator

from backend.schemas.common import BaseSchema, VideoStatus

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOWED_VIDEO_EXTENSIONS: frozenset[str] = frozenset(
    {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}
)
_VIDEO_ID_PREFIX: str = "vid_"
_CONTENT_TYPE_PATTERN: re.Pattern[str] = re.compile(r"^[a-z0-9!#$&^_.+-]+\/[a-z0-9!#$&^_.+-]+$")


# ---------------------------------------------------------------------------
# Status Enum (re-exported for convenience)
# ---------------------------------------------------------------------------

#: Video lifecycle status (see :class:`backend.schemas.common.VideoStatus`).
VideoStatus = VideoStatus


# ---------------------------------------------------------------------------
# Upload Request
# ---------------------------------------------------------------------------


class VideoUploadRequest(BaseSchema):
    """Request body for initiating a video upload.

    Attributes:
        filename: Original video filename (safe, allowed extension).
        file_size: File size in bytes (positive).
        content_type: Optional MIME type of the upload.

    Example:
        .. code-block:: json

            {
                "filename": "warehouse_1.mp4",
                "file_size": 1048576,
                "content_type": "video/mp4"
            }
    """

    filename: Annotated[
        str,
        Field(
            min_length=1,
            max_length=255,
            description="Original video filename.",
            examples=["warehouse_1.mp4"],
        ),
    ]
    file_size: Annotated[
        int,
        Field(
            gt=0,
            description="File size in bytes (positive).",
            examples=[1048576],
        ),
    ]
    content_type: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional MIME type of the upload.",
            examples=["video/mp4"],
        ),
    ] = None

    @field_validator("filename")
    @classmethod
    def _validate_filename(cls, value: str) -> str:
        """Validate the uploaded filename.

        Enforces:
        - non-empty after stripping
        - no path separators (no traversal)
        - length <= 255
        - allowed video extension

        Args:
            value: Raw filename.

        Returns:
            The stripped filename.

        Raises:
            ValueError: If any filename rule is violated.
        """
        name = value.strip()
        if not name:
            raise ValueError("Filename must not be empty.")

        if "/" in name or "\\" in name:
            raise ValueError(
                "Filename must not contain path separators ('/', '\\\\')."
            )

        if len(name) > 255:
            raise ValueError(
                f"Filename exceeds max length of 255: {len(name)}."
            )

        ext = Path(name).suffix.lower()
        if not ext:
            raise ValueError(f"Filename has no extension: '{name}'.")
        if ext not in _ALLOWED_VIDEO_EXTENSIONS:
            allowed = ", ".join(sorted(_ALLOWED_VIDEO_EXTENSIONS))
            raise ValueError(
                f"Extension '{ext}' is not allowed. "
                f"Allowed video extensions: {allowed}."
            )

        return name

    @field_validator("file_size")
    @classmethod
    def _validate_file_size(cls, value: int) -> int:
        """Ensure the file size is strictly positive.

        Args:
            value: File size in bytes.

        Returns:
            The validated size.

        Raises:
            ValueError: If the size is not positive.
        """
        if value <= 0:
            raise ValueError(f"file_size must be positive, got {value}.")
        return value

    @field_validator("content_type")
    @classmethod
    def _validate_content_type(cls, value: str | None) -> str | None:
        """Validate the optional content type string.

        Args:
            value: Raw MIME type.

        Returns:
            The normalized content type or ``None``.

        Raises:
            ValueError: If the content type is malformed.
        """
        if value is None:
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        if not _CONTENT_TYPE_PATTERN.match(normalized):
            raise ValueError(f"Invalid content type: '{value}'.")
        return normalized


# Backward/forward compatible alias used by the existing test suite.
UploadRequest = VideoUploadRequest


# ---------------------------------------------------------------------------
# Video Metadata
# ---------------------------------------------------------------------------


class VideoMetadata(BaseSchema):
    """Full metadata record for a video.

    Mirrors the record shape produced by
    :meth:`VideoProcessingService.initiate_upload
    <backend.services.video_service.VideoProcessingService.initiate_upload>`.

    Attributes:
        video_id: Unique video identifier (``vid_...``).
        filename: Original filename.
        file_size: File size in bytes.
        content_type: Optional MIME type.
        status: Lifecycle status.
        error_message: Optional error description.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
        processing_started_at: Optional processing start timestamp.
        processing_completed_at: Optional processing end timestamp.
        duration_seconds: Video duration in seconds.
        total_frames: Total number of frames.
        fps: Frames-per-second.
        thumbnail_path: Optional thumbnail file path.
        annotated_path: Optional annotated video output path.
    """

    video_id: Annotated[
        str,
        Field(
            min_length=1,
            description="Unique video identifier (prefix 'vid_').",
            examples=["vid_001"],
        ),
    ]
    filename: Annotated[
        str,
        Field(min_length=1, max_length=255, description="Original filename."),
    ]
    file_size: Annotated[
        int,
        Field(gt=0, description="File size in bytes."),
    ]
    content_type: Annotated[
        str | None,
        Field(default=None, description="Optional MIME type."),
    ] = None
    status: Annotated[
        VideoStatus,
        Field(default=VideoStatus.UPLOADED, description="Lifecycle status."),
    ] = VideoStatus.UPLOADED
    error_message: Annotated[
        str | None,
        Field(default=None, max_length=1000, description="Optional error."),
    ] = None
    created_at: Annotated[
        datetime,
        Field(description="ISO-8601 creation timestamp."),
    ]
    updated_at: Annotated[
        datetime,
        Field(description="ISO-8601 last-update timestamp."),
    ]
    processing_started_at: Annotated[
        datetime | None,
        Field(default=None, description="Optional processing start time."),
    ] = None
    processing_completed_at: Annotated[
        datetime | None,
        Field(default=None, description="Optional processing end time."),
    ] = None
    duration_seconds: Annotated[
        float,
        Field(default=0.0, ge=0.0, description="Video duration (seconds)."),
    ] = 0.0
    total_frames: Annotated[
        int,
        Field(default=0, ge=0, description="Total frame count."),
    ] = 0
    fps: Annotated[
        float,
        Field(default=0.0, ge=0.0, description="Frames per second."),
    ] = 0.0
    thumbnail_path: Annotated[
        str | None,
        Field(default=None, description="Optional thumbnail path."),
    ] = None
    annotated_path: Annotated[
        str | None,
        Field(default=None, description="Optional annotated video path."),
    ] = None

    @field_validator("video_id")
    @classmethod
    def _validate_video_id(cls, value: str) -> str:
        """Validate the video identifier prefix and non-emptiness.

        Args:
            value: The video identifier.

        Returns:
            The stripped identifier.

        Raises:
            ValueError: If the identifier is empty or lacks the prefix.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("video_id must not be empty.")
        if not stripped.startswith(_VIDEO_ID_PREFIX):
            raise ValueError(
                f"video_id must start with '{_VIDEO_ID_PREFIX}'."
            )
        return stripped

    @field_validator("created_at", "updated_at", "processing_started_at", "processing_completed_at", mode="before")
    @classmethod
    def _normalize_timestamps(
        cls, value: datetime | str | None
    ) -> datetime | None:
        """Normalize naive datetimes to timezone-aware UTC.

        Args:
            value: Raw timestamp or ``None``.

        Returns:
            UTC-aware datetime or ``None``.
        """
        if value is None:
            return None
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            parsed = value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @field_validator("filename")
    @classmethod
    def _validate_filename_present(cls, value: str) -> str:
        """Reject empty filenames in metadata records.

        Args:
            value: The raw filename.

        Returns:
            The stripped filename.

        Raises:
            ValueError: If the filename is empty.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("filename must not be empty.")
        return stripped


# ---------------------------------------------------------------------------
# Video Response
# ---------------------------------------------------------------------------


class VideoResponse(BaseSchema):
    """Video metadata payload returned to API clients.

    A subset of :class:`VideoMetadata` focused on the fields most
    commonly consumed by dashboard and client applications.

    Attributes:
        video_id: Unique video identifier.
        filename: Original filename.
        file_size: File size in bytes.
        content_type: Optional MIME type.
        status: Lifecycle status.
        error_message: Optional error description.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
        duration_seconds: Video duration in seconds.
        total_frames: Total frame count.
        fps: Frames per second.
        thumbnail_path: Optional thumbnail path.
        annotated_path: Optional annotated video path.
    """

    video_id: Annotated[
        str,
        Field(min_length=1, description="Unique video identifier."),
    ]
    filename: Annotated[
        str,
        Field(min_length=1, max_length=255, description="Original filename."),
    ]
    file_size: Annotated[
        int,
        Field(gt=0, description="File size in bytes."),
    ]
    content_type: Annotated[
        str | None,
        Field(default=None, description="Optional MIME type."),
    ] = None
    status: Annotated[
        VideoStatus,
        Field(description="Lifecycle status."),
    ]
    error_message: Annotated[
        str | None,
        Field(default=None, max_length=1000, description="Optional error."),
    ] = None
    created_at: Annotated[
        datetime,
        Field(description="ISO-8601 creation timestamp."),
    ]
    updated_at: Annotated[
        datetime,
        Field(description="ISO-8601 last-update timestamp."),
    ]
    duration_seconds: Annotated[
        float,
        Field(default=0.0, ge=0.0, description="Video duration (seconds)."),
    ] = 0.0
    total_frames: Annotated[
        int,
        Field(default=0, ge=0, description="Total frame count."),
    ] = 0
    fps: Annotated[
        float,
        Field(default=0.0, ge=0.0, description="Frames per second."),
    ] = 0.0
    thumbnail_path: Annotated[
        str | None,
        Field(default=None, description="Optional thumbnail path."),
    ] = None
    annotated_path: Annotated[
        str | None,
        Field(default=None, description="Optional annotated video path."),
    ] = None

    @field_validator("video_id")
    @classmethod
    def _validate_response_video_id(cls, value: str) -> str:
        """Reject empty video identifiers.

        Args:
            value: The video identifier.

        Returns:
            The stripped identifier.

        Raises:
            ValueError: If empty.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("video_id must not be empty.")
        return stripped

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _normalize_response_timestamps(
        cls, value: datetime | str
    ) -> datetime:
        """Normalize naive datetimes to timezone-aware UTC.

        Args:
            value: Raw timestamp.

        Returns:
            UTC-aware datetime.
        """
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            parsed = value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Processing Request
# ---------------------------------------------------------------------------


class VideoProcessingRequest(BaseSchema):
    """Request body for triggering video processing.

    Attributes:
        video_id: Unique video identifier (``vid_...``).
        options: Optional processing options (frame skip, confidence
            overrides, etc.).

    Example:
        .. code-block:: json

            {
                "video_id": "vid_001",
                "options": {
                    "confidence_threshold": 0.6,
                    "frame_skip": 5
                }
            }
    """

    video_id: Annotated[
        str,
        Field(
            min_length=1,
            description="Unique video identifier (prefix 'vid_').",
            examples=["vid_001"],
        ),
    ]
    options: Annotated[
        dict[str, object] | None,
        Field(
            default=None,
            description=(
                "Optional processing parameters (frame skip, confidence "
                "overrides, etc.)."
            ),
        ),
    ] = None

    @field_validator("video_id")
    @classmethod
    def _validate_processing_video_id(cls, value: str) -> str:
        """Validate the video identifier for processing.

        Args:
            value: The video identifier.

        Returns:
            The stripped identifier.

        Raises:
            ValueError: If empty or missing the expected prefix.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("video_id must not be empty.")
        if not stripped.startswith(_VIDEO_ID_PREFIX):
            raise ValueError(
                f"Invalid video_id format. Expected prefix '{_VIDEO_ID_PREFIX}'."
            )
        return stripped


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "VideoUploadRequest",
    "UploadRequest",
    "VideoMetadata",
    "VideoResponse",
    "VideoProcessingRequest",
    "VideoStatus",
]

