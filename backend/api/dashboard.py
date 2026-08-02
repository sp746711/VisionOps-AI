"""VisionOps AI — Dashboard API Endpoints.

Exposes dashboard summary, statistics, alerts, and performance endpoints
over HTTP. These routes are a thin boundary over
:class:`~backend.services.dashboard_service.DashboardService` and use the
existing dashboard schemas from :mod:`backend.schemas.dashboard`.

Implemented endpoints:
    - ``GET    /dashboard`` — full dashboard response.
    - ``GET    /dashboard/summary`` — overall dashboard summary.
    - ``GET    /dashboard/stats`` — detection statistics.
    - ``GET    /dashboard/alerts`` — alert summary.
    - ``GET    /dashboard/performance`` — performance metrics.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_dashboard_service
from backend.schemas.dashboard import (
    DashboardResponse,
    DashboardSummary,
    DashboardStatistics,
    AlertSummary,
    PerformanceMetrics,
)
from backend.services import DashboardService

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "",
    summary="Full dashboard response",
    description=(
        "Returns a comprehensive dashboard payload combining summary, "
        "statistics, alert summary, and performance metrics."
    ),
)
async def get_dashboard(
    days: int = Query(
        default=7,
        ge=1,
        le=365,
        description="Number of days for performance metrics.",
    ),
    dashboard_service: Annotated[
        DashboardService, Depends(get_dashboard_service)
    ] = ...,
) -> Any:
    """Get the full dashboard response.

    Args:
        days: Look-back period for performance metrics.
        dashboard_service: Injected dashboard service.

    Returns:
        A dictionary with summary, statistics, alert_summary, and
        performance_metrics keys.
    """
    summary = dashboard_service.get_summary()
    stats = dashboard_service.get_detection_stats()
    alerts = dashboard_service.get_alert_summary()
    performance = dashboard_service.get_performance_metrics(days=days)

    return {
        "summary": summary,
        "statistics": stats,
        "alert_summary": alerts,
        "performance_metrics": performance,
    }


@router.get(
    "/summary",
    response_model=DashboardSummary,
    summary="Get dashboard summary",
    description=(
        "Returns overall dashboard summary counts including total videos, "
        "detections, events, alerts, and KPIs."
    ),
)
async def get_summary(
    dashboard_service: Annotated[
        DashboardService, Depends(get_dashboard_service)
    ] = ...,
) -> Any:
    """Get the overall dashboard summary.

    Args:
        dashboard_service: Injected dashboard service.

    Returns:
        :class:`DashboardSummary` with high-level counts.
    """
    return dashboard_service.get_summary()


@router.get(
    "/stats",
    response_model=DashboardStatistics,
    summary="Get detection statistics",
    description=(
        "Returns detection statistics including total counts, unique "
        "classes, average confidence, top classes, and confidence "
        "distribution."
    ),
)
async def get_stats(
    video_id: str | None = Query(
        default=None,
        description="Optional video ID to scope statistics.",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of top class entries.",
    ),
    dashboard_service: Annotated[
        DashboardService, Depends(get_dashboard_service)
    ] = ...,
) -> Any:
    """Get detection statistics.

    Args:
        video_id: Optional video identifier to scope statistics.
        limit: Maximum number of top class entries.
        dashboard_service: Injected dashboard service.

    Returns:
        :class:`DashboardStatistics` with detection stats.
    """
    return dashboard_service.get_detection_stats(
        video_id=video_id,
        limit=limit,
    )


@router.get(
    "/alerts",
    response_model=AlertSummary,
    summary="Get alert summary",
    description=(
        "Returns an aggregated alert summary with severity distribution "
        "and recent alerts."
    ),
)
async def get_alerts(
    min_severity: str = Query(
        default="low",
        description="Minimum severity level (low, medium, high, critical).",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of recent alerts.",
    ),
    dashboard_service: Annotated[
        DashboardService, Depends(get_dashboard_service)
    ] = ...,
) -> Any:
    """Get the alert summary.

    Args:
        min_severity: Minimum severity to include.
        limit: Maximum number of recent alerts.
        dashboard_service: Injected dashboard service.

    Returns:
        :class:`AlertSummary` with alert data.
    """
    return dashboard_service.get_alert_summary(
        min_severity=min_severity,
        limit=limit,
    )


@router.get(
    "/performance",
    response_model=PerformanceMetrics,
    summary="Get performance metrics",
    description=(
        "Returns processing performance metrics for the specified "
        "look-back period."
    ),
)
async def get_performance(
    days: int = Query(
        default=7,
        ge=1,
        le=365,
        description="Number of days to look back.",
    ),
    dashboard_service: Annotated[
        DashboardService, Depends(get_dashboard_service)
    ] = ...,
) -> Any:
    """Get system performance metrics.

    Args:
        days: Look-back period in days.
        dashboard_service: Injected dashboard service.

    Returns:
        :class:`PerformanceMetrics` with processing stats.
    """
    return dashboard_service.get_performance_metrics(days=days)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["router"]
