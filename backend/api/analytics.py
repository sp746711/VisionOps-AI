"""VisionOps AI — Analytics API Endpoints.

Exposes analytics pipeline, KPI, spoilage, and freshness endpoints over HTTP.
These routes are a thin boundary over
:class:`~backend.services.analytics_service.AnalyticsService` and use the
existing analytics schemas from :mod:`backend.schemas.analytics`.

Implemented endpoints:
    - ``POST   /analytics/pipeline`` — run the analytics pipeline.
    - ``GET    /analytics/kpis`` — retrieve KPI records.
    - ``GET    /analytics/spoilage`` — compute spoilage metrics.
    - ``GET    /analytics/freshness`` — compute freshness metrics.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_analytics_service
from backend.schemas.analytics import (
    AnalyticsRequest,
    AnalyticsResponse,
    KPIResponse,
)
from backend.services import AnalyticsService

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/pipeline",
    response_model=AnalyticsResponse,
    status_code=202,
    summary="Run analytics pipeline",
    description=(
        "Triggers the analytics pipeline for the specified operation. "
        "The pipeline aggregates data, computes KPIs, and refreshes "
        "dashboard datasets as configured."
    ),
)
async def run_pipeline(
    payload: AnalyticsRequest,
    analytics_service: Annotated[
        AnalyticsService, Depends(get_analytics_service)
    ] = ...,
) -> Any:
    """Run the analytics pipeline.

    Args:
        payload: Validated analytics request with operation and filters.
        analytics_service: Injected analytics service.

    Returns:
        :class:`AnalyticsResponse` with pipeline execution results.
    """
    filters: dict[str, Any] = {}
    if payload.video_id:
        filters["video_id"] = payload.video_id
    if payload.date_from:
        filters["date_from"] = payload.date_from
    if payload.date_to:
        filters["date_to"] = payload.date_to

    result = await analytics_service.run_pipeline(
        operation=payload.operation.value,
        filters=filters,
    )

    return AnalyticsResponse(
        operation=result.get("operation", payload.operation.value),
        status=result.get("status", "completed"),
        aggregation=result.get("aggregation"),
        kpis=result.get("kpis"),
        message=f"Analytics pipeline '{payload.operation.value}' completed.",
    )


@router.get(
    "/kpis",
    summary="Retrieve KPI records",
    description=(
        "Returns key performance indicator records, optionally scoped "
        "to a specific video."
    ),
)
async def get_kpis(
    video_id: str | None = Query(
        default=None,
        description="Optional video ID to scope KPIs.",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=10000,
        description="Maximum number of KPI records to return.",
    ),
    analytics_service: Annotated[
        AnalyticsService, Depends(get_analytics_service)
    ] = ...,
) -> Any:
    """Retrieve KPI records.

    Args:
        video_id: Optional video identifier to scope KPIs.
        limit: Maximum number of records to return.
        analytics_service: Injected analytics service.

    Returns:
        List of KPI dictionaries.
    """
    return analytics_service.calculate_kpis(
        video_id=video_id,
        limit=limit,
    )


@router.get(
    "/spoilage",
    summary="Compute spoilage metrics",
    description=(
        "Computes spoilage-related metrics including spoilage risk index, "
        "high-risk detection count, and contributing risk factors."
    ),
)
async def get_spoilage_metrics(
    video_id: str | None = Query(
        default=None,
        description="Optional video ID to scope metrics.",
    ),
    analytics_service: Annotated[
        AnalyticsService, Depends(get_analytics_service)
    ] = ...,
) -> Any:
    """Compute spoilage metrics.

    Args:
        video_id: Optional video identifier to scope metrics.
        analytics_service: Injected analytics service.

    Returns:
        Dictionary with spoilage metrics.
    """
    return analytics_service.compute_spoilage_metrics(video_id=video_id)


@router.get(
    "/freshness",
    summary="Compute freshness metrics",
    description=(
        "Computes freshness-related metrics including freshness score, "
        "turnover rate, and stale detection ratio."
    ),
)
async def get_freshness_metrics(
    video_id: str | None = Query(
        default=None,
        description="Optional video ID to scope metrics.",
    ),
    analytics_service: Annotated[
        AnalyticsService, Depends(get_analytics_service)
    ] = ...,
) -> Any:
    """Compute freshness metrics.

    Args:
        video_id: Optional video identifier to scope metrics.
        analytics_service: Injected analytics service.

    Returns:
        Dictionary with freshness metrics.
    """
    return analytics_service.compute_freshness_metrics(video_id=video_id)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["router"]
