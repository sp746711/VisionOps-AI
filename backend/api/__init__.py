"""VisionOps AI — API Layer.

This package contains the FastAPI HTTP boundary for the VisionOps AI
backend.  Each module maps to a domain router that delegates to the
existing service layer.

Modules:
    - :mod:`backend.api.dependencies` — reusable FastAPI dependencies.
    - :mod:`backend.api.health` — liveness/readiness endpoints.
    - :mod:`backend.api.auth` — authentication endpoints.
    - :mod:`backend.api.videos` — video management endpoints.
    - :mod:`backend.api.analysis` — detection-analysis endpoints.
    - :mod:`backend.api.analytics` — analytics/KPI endpoints.
    - :mod:`backend.api.dashboard` — dashboard endpoints.
    - :mod:`backend.api.reports` — report-generation endpoints.
    - :mod:`backend.api.settings` — settings endpoints.
    - :mod:`backend.api.router` — the central API router.

Importing this package has no heavy side effects: it does **not**
instantiate a FastAPI app, start services, or load AI models.
"""

from backend.api.router import api_router

__all__ = ["api_router"]

