"""VisionOps AI — Central API Router.

Aggregates all domain-specific sub-routers from the ``backend.api`` package
into a single ``api_router`` that is mounted by :mod:`backend.main`.

Each sub-router is imported and included exactly once to avoid duplicate
route registration.

Routers registered:
    - :mod:`backend.api.health` — liveness/readiness probes.
    - :mod:`backend.api.auth` — authentication endpoints.
    - :mod:`backend.api.videos` — video management endpoints.
    - :mod:`backend.api.analysis` — detection analysis endpoints.
    - :mod:`backend.api.analytics` — analytics/KPI endpoints.
    - :mod:`backend.api.dashboard` — dashboard endpoints.
    - :mod:`backend.api.reports` — report generation endpoints.
    - :mod:`backend.api.settings` — settings management endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.core.config import settings
from backend.api import (
    analysis,
    analytics,
    auth,
    dashboard,
    health,
    reports,
    settings as settings_module,
    videos,
)

# ---------------------------------------------------------------------------
# Central API Router
# ---------------------------------------------------------------------------

api_router = APIRouter(prefix=settings.API_PREFIX)

# ---------------------------------------------------------------------------
# Register sub-routers
# ---------------------------------------------------------------------------

api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(videos.router)
api_router.include_router(analysis.router)
api_router.include_router(analytics.router)
api_router.include_router(dashboard.router)
api_router.include_router(reports.router)
api_router.include_router(settings_module.router)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["api_router"]
