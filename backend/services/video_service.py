"""VisionOps AI — Video Processing Service.

Provides business-logic orchestration for video upload, processing, metadata
management, and status tracking. Delegates all low-level I/O to the storage
layer and all AI/ML operations to the AI pipeline.

Responsibilities:
    - Upload workflow coordination
    - Processing workflow coordination
    - Video metadata management
    - Status tracking (uploaded, queued, processing, completed, failed)
    - Video listing and filtering

Usage::

    from backend.services import VideoProcessingService

    service = VideoProcessingService()
    result = await service.process_video(video_id="abc-123", options={...})
    metadata = service.get_video_metadata(video_id="abc-123")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.core.config import settings
from backend.exceptions import (
    ValidationError,
    StorageError,
    FileValidationError,
    FileOperationError,
)
from backend.storage import StorageService
from backend.utils.date_utils import now_utc
from backend.utils.id_generator import generate_uuid4
from backend.utils.validation import validate_uuid

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VIDEO_ID_PREFIX: str = "vid_"
_ALLOWED_STATUSES: frozenset[str] = frozenset(
    {"uploaded", "queued", "processing", "completed", "failed", "cancelled"}
)

# ---------------------------------------------------------------------------
# VideoProcessingService
# ---------------------------------------------------------------------------


class VideoProcessingService:
    """Orchestrates video upload, processing, and metadata management.

    This service sits between the API layer and the storage/AI layers.
    It coordinates workflows, validates inputs, manages status transitions,
    and ensures data consistency — without implementing any low-level I/O
    or AI inference logic.

    Dependency injection is used for the storage layer to improve
    testability.

    Raises:
        ValidationError: If input arguments are invalid.
        StorageError: If storage operations fail.
        FileOperationError: If file operations fail.
    """

    def __init__(
        self,
        storage: StorageService | None = None,
    ) -> None:
        """Initialise the video processing service.

        Args:
            storage: Injected ``StorageService`` instance. When ``None``,
                a default instance is created.
        """
        self._storage = storage or StorageService()
        logger.info(
            "VideoProcessingService initialised (storage=%s)",
            type(self._storage).__name__,
        )

    # ------------------------------------------------------------------
    # Upload Workflow
    # ------------------------------------------------------------------

    def initiate_upload(
        self,
        filename: str,
        file_size: int,
        content_type: str | None = None,
    ) -> dict[str, Any]:
        """Initiate a video upload workflow.

        Validates the filename and size against configured constraints,
        generates a unique video ID, and persists an initial metadata
        record.

        Args:
            filename: Original filename of the uploaded video.
            file_size: File size in bytes.
            content_type: Optional MIME type of the upload.

        Returns:
            Dictionary with keys:
            - ``video_id``: Generated unique video identifier.
            - ``filename``: Original filename.
            - ``file_size``: File size in bytes.
            - ``status``: Initial status (``"uploaded"``).
            - ``created_at``: ISO-8601 timestamp.

        Raises:
            ValidationError: If *filename* or *file_size* are invalid.
            StorageError: If persisting metadata fails.
        """
        logger.info(
            "Initiating upload: filename='%s', size=%d bytes",
            filename,
            file_size,
        )

        # --- Validate filename ---
        if not filename or not filename.strip():
            raise ValidationError("Filename must not be empty.")

        ext = Path(filename).suffix.lower()
        allowed = settings.ALLOWED_VIDEO_EXTENSIONS
        if ext not in allowed:
            raise ValidationError(
                f"Extension '{ext}' is not allowed. "
                f"Allowed: {', '.join(allowed)}"
            )

        # --- Validate file size ---
        if file_size <= 0:
            raise ValidationError(
                f"File size must be positive, got {file_size}."
            )
        if file_size > settings.UPLOAD_MAX_SIZE:
            max_mb = settings.UPLOAD_MAX_SIZE / (1024 * 1024)
            raise ValidationError(
                f"File size ({file_size} bytes) exceeds maximum "
                f"upload size ({max_mb:.1f} MB)."
            )

        # --- Generate video ID ---
        video_id = f"{_VIDEO_ID_PREFIX}{generate_uuid4()}"

        # --- Build metadata record ---
        now = now_utc()
        record: dict[str, Any] = {
            "video_id": video_id,
            "filename": filename.strip(),
            "file_size": file_size,
            "content_type": content_type or "",
            "status": "uploaded",
            "error_message": "",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "processing_started_at": "",
            "processing_completed_at": "",
            "duration_seconds": 0.0,
            "total_frames": 0,
            "fps": 0.0,
            "thumbnail_path": "",
            "annotated_path": "",
        }

        # --- Persist to CSV store ---
        try:
            self._storage.append_csv_store("videos", [record])
        except StorageError as exc:
            logger.error("Failed to persist video metadata: %s", exc)
            raise StorageError(
                f"Failed to initiate upload for '{filename}': {exc}"
            ) from exc

        logger.info(
            "Upload initiated: video_id='%s', filename='%s'",
            video_id,
            filename,
        )
        return record

    # ------------------------------------------------------------------
    # Processing Workflow
    # ------------------------------------------------------------------

    async def process_video(
        self,
        video_id: str,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Orchestrate video processing.

        This method is called by the ``VideoProcessingWorker``. It
        validates the video ID, updates status to ``processing``,
        delegates AI inference to the pipeline (via storage / AI
        coordination), and persists results.

        **Current implementation** validates and transitions status only
        — the actual AI pipeline invocation will be wired when the
        ``backend.ai`` package is finalised.

        Args:
            video_id: Unique video identifier.
            options: Optional processing parameters (e.g. frame skip,
                confidence threshold overrides).

        Returns:
            Dictionary with processing result metadata.

        Raises:
            ValidationError: If *video_id* is invalid.
            StorageError: If video metadata cannot be read or updated.
        """
        logger.info(
            "Processing video: video_id='%s', options=%s",
            video_id,
            options or {},
        )

        # --- Validate video_id ---
        if not video_id or not video_id.startswith(_VIDEO_ID_PREFIX):
            raise ValidationError(
                f"Invalid video_id format: '{video_id}'. "
                f"Expected prefix '{_VIDEO_ID_PREFIX}'."
            )

        # --- Fetch current metadata ---
        records = self._storage.read_csv_store("videos")
        target: dict[str, Any] | None = None
        for record in records:
            if record.get("video_id") == video_id:
                target = record
                break

        if target is None:
            raise FileValidationError(
                f"Video not found: '{video_id}'."
            )

        current_status = target.get("status", "")
        if current_status == "processing":
            raise ValidationError(
                f"Video '{video_id}' is already being processed."
            )
        if current_status == "completed":
            logger.warning(
                "Video '%s' is already completed. Re-processing.",
                video_id,
            )

        # --- Transition to processing ---
        now = now_utc()
        update_data: dict[str, Any] = {
            "status": "processing",
            "updated_at": now.isoformat(),
            "processing_started_at": now.isoformat(),
            "error_message": "",
        }

        def match_fn(row: dict[str, Any]) -> bool:
            return row.get("video_id") == video_id

        def update_fn(row: dict[str, Any]) -> dict[str, Any]:
            row.update(update_data)
            return row

        try:
            self._storage.csv_manager.update_rows("videos", match_fn, update_fn)
        except StorageError as exc:
            logger.error(
                "Failed to update video '%s' status: %s",
                video_id,
                exc,
            )
            raise StorageError(
                f"Failed to start processing for video '{video_id}': {exc}"
            ) from exc

        logger.info(
            "Video '%s' status transitioned to 'processing'.",
            video_id,
        )

        # TODO: Wire actual AI pipeline invocation here once available.
        #   from backend.ai.pipeline import AIPipeline
        #   pipeline = AIPipeline()
        #   result = await pipeline.process_video(
        #       video_path=...,
        #       options=options or {},
        #   )

        return {
            "video_id": video_id,
            "status": "processing",
            "message": f"Video '{video_id}' is now being processed.",
            "options": options or {},
        }

    def mark_completed(
        self,
        video_id: str,
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Mark a video as successfully processed.

        Args:
            video_id: Unique video identifier.
            result: Optional processing result metadata (duration, frames,
                etc.) to merge into the record.

        Returns:
            Updated video metadata dictionary.

        Raises:
            ValidationError: If *video_id* is invalid.
            StorageError: If the update fails.
        """
        now = now_utc()
        update_data: dict[str, Any] = {
            "status": "completed",
            "updated_at": now.isoformat(),
            "processing_completed_at": now.isoformat(),
        }
        if result:
            update_data.update(result)

        try:
            updated = self._update_video_record(video_id, update_data)
        except StorageError as exc:
            raise StorageError(
                f"Failed to mark video '{video_id}' as completed: {exc}"
            ) from exc

        logger.info("Video '%s' marked as completed.", video_id)
        return updated

    def mark_failed(
        self,
        video_id: str,
        error_message: str,
    ) -> dict[str, Any]:
        """Mark a video as failed.

        Args:
            video_id: Unique video identifier.
            error_message: Description of the failure.

        Returns:
            Updated video metadata dictionary.

        Raises:
            ValidationError: If *video_id* is invalid.
            StorageError: If the update fails.
        """
        now = now_utc()
        update_data: dict[str, Any] = {
            "status": "failed",
            "updated_at": now.isoformat(),
            "processing_completed_at": now.isoformat(),
            "error_message": error_message[:1000],
        }

        try:
            updated = self._update_video_record(video_id, update_data)
        except StorageError as exc:
            raise StorageError(
                f"Failed to mark video '{video_id}' as failed: {exc}"
            ) from exc

        logger.error("Video '%s' marked as failed: %s", video_id, error_message)
        return updated

    # ------------------------------------------------------------------
    # Metadata Management
    # ------------------------------------------------------------------

    def get_video_metadata(self, video_id: str) -> dict[str, Any]:
        """Retrieve metadata for a single video.

        Args:
            video_id: Unique video identifier.

        Returns:
            Video metadata dictionary.

        Raises:
            ValidationError: If *video_id* is invalid.
            FileValidationError: If the video is not found.
        """
        if not video_id:
            raise ValidationError("video_id must not be empty.")

        try:
            records = self._storage.read_csv_store("videos")
        except StorageError as exc:
            raise StorageError(
                f"Failed to read video metadata: {exc}"
            ) from exc

        for record in records:
            if record.get("video_id") == video_id:
                return record

        raise FileValidationError(f"Video not found: '{video_id}'.")

    def update_metadata(
        self,
        video_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update specific fields of a video's metadata.

        Only allowed fields (non-system) can be updated. System fields
        like ``video_id``, ``created_at``, ``status`` are protected.

        Args:
            video_id: Unique video identifier.
            updates: Dictionary of fields to update.

        Returns:
            Updated video metadata dictionary.

        Raises:
            ValidationError: If *video_id* is invalid or protected fields
                are included.
            FileValidationError: If the video is not found.
            StorageError: If the update fails.
        """
        _protected: frozenset[str] = frozenset(
            {"video_id", "created_at"}
        )

        if not video_id:
            raise ValidationError("video_id must not be empty.")

        protected_keys = _protected & set(updates.keys())
        if protected_keys:
            raise ValidationError(
                f"Cannot update protected fields: {', '.join(protected_keys)}"
            )

        updates["updated_at"] = now_utc().isoformat()

        try:
            return self._update_video_record(video_id, updates)
        except (StorageError, FileValidationError) as exc:
            raise StorageError(
                f"Failed to update metadata for video '{video_id}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Status Tracking
    # ------------------------------------------------------------------

    def get_video_status(self, video_id: str) -> str:
        """Return the processing status of a video.

        Args:
            video_id: Unique video identifier.

        Returns:
            Status string (one of ``uploaded``, ``queued``, ``processing``,
            ``completed``, ``failed``, ``cancelled``).

        Raises:
            ValidationError: If *video_id* is invalid.
            FileValidationError: If the video is not found.
        """
        metadata = self.get_video_metadata(video_id)
        return metadata.get("status", "unknown")

    def list_videos(
        self,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List videos with optional status filtering and pagination.

        Args:
            status: Optional status filter. If ``None``, all statuses
                are returned.
            limit: Maximum number of records to return (default: 100).
            offset: Number of records to skip (default: 0).

        Returns:
            List of video metadata dictionaries.

        Raises:
            ValidationError: If *status* is invalid or pagination params
                are out of range.
            StorageError: If reading the store fails.
        """
        if status is not None and status not in _ALLOWED_STATUSES:
            raise ValidationError(
                f"Invalid status '{status}'. "
                f"Allowed: {', '.join(sorted(_ALLOWED_STATUSES))}."
            )

        if limit < 1 or limit > 1000:
            raise ValidationError(
                f"limit must be between 1 and 1000, got {limit}."
            )
        if offset < 0:
            raise ValidationError(
                f"offset must be non-negative, got {offset}."
            )

        try:
            all_videos = self._storage.read_csv_store("videos")
        except StorageError as exc:
            raise StorageError(
                f"Failed to list videos: {exc}"
            ) from exc

        # Filter by status
        if status:
            filtered = [
                v for v in all_videos
                if v.get("status") == status
            ]
        else:
            filtered = list(all_videos)

        # Apply pagination
        paginated = filtered[offset:offset + limit]

        logger.debug(
            "Listed %d videos (status=%s, limit=%d, offset=%d, total=%d)",
            len(paginated),
            status or "all",
            limit,
            offset,
            len(filtered),
        )
        return paginated

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _update_video_record(
        self,
        video_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Apply updates to a single video record by video_id.

        Args:
            video_id: Unique video identifier.
            updates: Dictionary of fields to update.

        Returns:
            The updated video metadata dictionary.

        Raises:
            FileValidationError: If the video is not found.
            StorageError: If the update operation fails.
        """
        found_record: dict[str, Any] | None = None

        def match_fn(row: dict[str, Any]) -> bool:
            return row.get("video_id") == video_id

        def update_fn(row: dict[str, Any]) -> dict[str, Any]:
            nonlocal found_record
            row.update(updates)
            found_record = dict(row)
            return row

        try:
            updated_count = self._storage.csv_manager.update_rows(
                "videos", match_fn, update_fn
            )
        except StorageError as exc:
            raise StorageError(
                f"Failed to update video '{video_id}': {exc}"
            ) from exc

        if updated_count == 0:
            raise FileValidationError(
                f"Video not found: '{video_id}'."
            )

        return found_record or {}

