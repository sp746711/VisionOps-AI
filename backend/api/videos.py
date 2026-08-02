"""VisionOps AI — Video Management API Endpoints.

Exposes video upload initiation, metadata, status, processing, and listing
as HTTP endpoints.  These routes are a thin HTTP boundary over
:class:`~backend.services.video_service.VideoProcessingService` and use the
existing Pydantic schemas in :mod:`backend.schemas.video`.

The API layer never touches the AI pipeline directly — all processing is
delegated to :class:`VideoProcessingService`.

Implemented endpoints:
    - ``POST   /videos/upload`` — initiate a video upload.
    - ``GET    /videos`` — list videos (status filter + pagination).
    - ``GET    /videos/{video_id}`` — fetch video metadata.
    - ``GET    /videos/{video_id}/status`` — fetch processing status.
    - ``POST   /videos/{video_id}/process`` — trigger processing.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_video_service
from backend.schemas.common import VideoStatus
from backend.schemas.response import SuccessResponse
from backend.schemas.video import (
    VideoProcessingRequest,
    VideoResponse,
    VideoUploadRequest,
)
from backend.services import VideoProcessingService

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/videos", tags=["Videos"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=VideoResponse,
    status_code=201,
    summary="Initiate a video upload",
    description=(
        "Validates the provided filename and size, registers the upload "
        "in the video store, and returns the created metadata."
    ),
)
async def upload_video(
    payload: VideoUploadRequest,
    video_service: Annotated[
        VideoProcessingService, Depends(get_video_service)
    ] = ...,
) -> Any:
    """Initiate a video upload workflow.

    Args:
        payload: Validated upload metadata.
        video_service: Injected video processing service.

    Returns:
        :class:`VideoResponse` containing the created video metadata.
    """
    return video_service.initiate_upload(
        filename=payload.filename,
        file_size=payload.file_size,
        content_type=payload.content_type,
    )


@router.get(
    "",
    summary="List videos",
    description=(
        "Returns a paginated list of video metadata, optionally filtered "
        "by processing status."
    ),
)
async def list_videos(
    status: Annotated[
        VideoStatus | None, Query(description="Optional status filter.")
    ] = None,
    limit: Annotated[
        int, Query(ge=1, le=1000, description="Maximum items per page.")
    ] = 100,
    offset: Annotated[
        int, Query(ge=0, description="Number of items to skip.")
    ] = 0,
    video_service: Annotated[
        VideoProcessingService, Depends(get_video_service)
    ] = ...,
) -> Any:
    """List videos with optional status filtering and pagination.

    Args:
        status: Optional lifecycle status filter.
        limit: Maximum number of items to return.
        offset: Number of items to skip.
        video_service: Injected video processing service.

    Returns:
        A pagination envelope with ``items``, ``total``, ``limit`` and
        ``offset``.
    """
    status_value = status.value if status is not None else None
    items = video_service.list_videos(
        status=status_value, limit=limit, offset=offset
    )
    # The service has no count method; fetch a large page to compute total.
    total = len(
        video_service.list_videos(
            status=status_value, limit=1000, offset=0
        )
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/{video_id}",
    summary="Get video metadata",
    description="Returns the full metadata record for a single video.",
)
async def get_video(
    video_id: str,
    video_service: Annotated[
        VideoProcessingService, Depends(get_video_service)
    ] = ...,
) -> Any:
    """Fetch metadata for a single video.

    Args:
        video_id: Unique video identifier.
        video_service: Injected video processing service.

    Returns:
        Video metadata record.

    Raises:
        FileValidationError: If the video does not exist (HTTP 400).
    """
    return video_service.get_video_metadata(video_id=video_id)


@router.get(
    "/{video_id}/status",
    summary="Get video processing status",
    description="Returns the current lifecycle status of a single video.",
)
async def get_video_status(
    video_id: str,
    video_service: Annotated[
        VideoProcessingService, Depends(get_video_service)
    ] = ...,
) -> Any:
    """Fetch the processing status of a video.

    Args:
        video_id: Unique video identifier.
        video_service: Injected video processing service.

    Returns:
        A dictionary with ``video_id`` and ``status`` keys.

    Raises:
        FileValidationError: If the video does not exist (HTTP 400).
    """
    status = video_service.get_video_status(video_id=video_id)
    return {"video_id": video_id, "status": status}


@router.post(
    "/{video_id}/process",
    response_model=SuccessResponse,
    status_code=202,
    summary="Trigger video processing",
    description=(
        "Triggers the processing workflow for a video.  The actual AI "
        "inference is delegated to the service layer."
    ),
)
async def process_video(
    payload: VideoProcessingRequest,
    video_service: Annotated[
        VideoProcessingService, Depends(get_video_service)
    ] = ...,
) -> Any:
    """Trigger processing for a video.

    Args:
        payload: Validated processing request with ``video_id`` and
            optional options.
        video_service: Injected video processing service.

    Returns:
        :class:`SuccessResponse` indicating the processing was accepted.
    """
    result = await video_service.process_video(
        video_id=payload.video_id,
        options=payload.options,
    )
    return SuccessResponse(
        message=result.get("message", "Video processing accepted."),
        data=result,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["router"]

