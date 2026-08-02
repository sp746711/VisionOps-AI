"""VisionOps AI — Health Check API Endpoints.

Provides a lightweight liveness endpoint for the API layer.  Health
endpoints deliberately avoid loading AI models, opening videos, running
analytics, or scanning the filesystem, keeping the probe cheap.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.core.config import settings

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["Health"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    summary="Liveness probe",
    description=(
        "Returns a lightweight liveness response indicating the API "
        "process is running.  No heavy resources are touched."
    ),
)
async def health() -> dict[str, Any]:
    """Return a liveness payload.

    Returns:
        A dictionary with ``status`` and ``version`` keys.
    """
    return {
        "status": "healthy",
        "version": settings.VERSION,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["router"]

