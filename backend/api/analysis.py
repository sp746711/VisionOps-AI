"""VisionOps AI — Analysis API Endpoints.

Exposes detection analysis, aggregation, and summary endpoints over HTTP.
These routes are a thin boundary over
:class:`~backend.services.analysis_service.AnalysisService` and use the
existing analysis schemas from :mod:`backend.schemas.analysis`.

Implemented endpoints:
    - ``POST   /analysis/detect`` — run detection analysis on a video.
    - ``GET    /analysis/aggregate/{video_id}`` — get aggregated results.
    - ``GET    /analysis/summary/{video_id}`` — get detection summary.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_analysis_service
from backend.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    DetectionSummary,
)
from backend.services import AnalysisService

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/analysis", tags=["Analysis"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/detect",
    response_model=AnalysisResponse,
    status_code=201,
    summary="Run detection analysis",
    description=(
        "Validates, filters, and persists detection results for a video. "
        "Returns the enriched detection records with an optional summary."
    ),
)
async def detect(
    payload: AnalysisRequest,
    analysis_service: Annotated[
        AnalysisService, Depends(get_analysis_service)
    ] = ...,
) -> Any:
    """Run detection analysis on a video.

    Args:
        payload: Validated analysis request with video_id and detections.
        analysis_service: Injected analysis service.

    Returns:
        :class:`AnalysisResponse` with enriched detection records.
    """
    result = analysis_service.run_detection(
        video_id=payload.video_id,
        detections=payload.detections,
        source_frame=payload.source_frame,
    )

    return AnalysisResponse(
        video_id=payload.video_id,
        total_detections=len(result),
        detections=result,
        message=f"Detection analysis completed for video '{payload.video_id}'.",
    )


@router.get(
    "/aggregate/{video_id}",
    summary="Get aggregated detection results",
    description=(
        "Returns aggregated detection statistics for a video, including "
        "per-class counts, average confidence, and detections per frame."
    ),
)
async def aggregate(
    video_id: str,
    analysis_service: Annotated[
        AnalysisService, Depends(get_analysis_service)
    ] = ...,
) -> Any:
    """Get aggregated detection results for a video.

    Args:
        video_id: Unique video identifier.
        analysis_service: Injected analysis service.

    Returns:
        Aggregated detection summary dictionary.
    """
    return analysis_service.aggregate_results(video_id=video_id)


@router.get(
    "/summary/{video_id}",
    response_model=DetectionSummary,
    summary="Get detection summary",
    description=(
        "Returns a lightweight summary of detections for a video, "
        "using cached data when available."
    ),
)
async def get_summary(
    video_id: str,
    analysis_service: Annotated[
        AnalysisService, Depends(get_analysis_service)
    ] = ...,
) -> Any:
    """Get detection summary for a video.

    Args:
        video_id: Unique video identifier.
        analysis_service: Injected analysis service.

    Returns:
        :class:`DetectionSummary` with key counts and stats.
    """
    return analysis_service.get_detection_summary(video_id=video_id)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["router"]
