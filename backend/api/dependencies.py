"""VisionOps AI — Reusable FastAPI Dependencies.

This module provides dependency providers for the service layer, plus an
authentication dependency used by protected endpoints.

Service providers are memoized (singleton) so expensive sub-dependencies
(e.g. the storage facade) are not rebuilt for every request.  Tests may
override any provider through ``app.dependency_overrides``.

The authentication dependency delegates token verification to
:class:`~backend.services.auth_service.AuthService` — it never
re-implements JWT logic.  When the request-level
:class:`~backend.middleware.authentication.AuthenticationMiddleware`
has already populated ``request.state.user``, that value is reused.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Iterator

from fastapi import Depends, Request

from backend.exceptions import AuthenticationError
from backend.services import (
    AnalysisService,
    AnalyticsService,
    AuthService,
    DashboardService,
    ReportService,
    SettingsService,
    VideoProcessingService,
)
from backend.storage import StorageService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_bearer_token(request: Request) -> str | None:
    """Extract a Bearer token from the ``Authorization`` header.

    Args:
        request: The incoming request.

    Returns:
        The token string, or ``None`` when the header is missing or
        malformed.
    """
    header: str | None = request.headers.get("Authorization")
    if not header:
        return None
    parts: list[str] = header.strip().split(" ", maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token: str = parts[1].strip()
    return token if token else None


# ---------------------------------------------------------------------------
# Service Providers
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_storage_service() -> StorageService:
    """Provide a shared :class:`StorageService` instance.

    Returns:
        A memoized :class:`StorageService`.
    """
    return StorageService()


@lru_cache(maxsize=1)
def get_auth_service() -> AuthService:
    """Provide a shared :class:`AuthService` instance.

    Returns:
        A memoized :class:`AuthService`.
    """
    return AuthService(storage=get_storage_service())


@lru_cache(maxsize=1)
def get_video_service() -> VideoProcessingService:
    """Provide a shared :class:`VideoProcessingService` instance.

    Returns:
        A memoized :class:`VideoProcessingService`.
    """
    return VideoProcessingService(storage=get_storage_service())


@lru_cache(maxsize=1)
def get_analysis_service() -> AnalysisService:
    """Provide a shared :class:`AnalysisService` instance.

    Returns:
        A memoized :class:`AnalysisService`.
    """
    return AnalysisService(storage=get_storage_service())


@lru_cache(maxsize=1)
def get_analytics_service() -> AnalyticsService:
    """Provide a shared :class:`AnalyticsService` instance.

    Returns:
        A memoized :class:`AnalyticsService`.
    """
    return AnalyticsService(storage=get_storage_service())


@lru_cache(maxsize=1)
def get_dashboard_service() -> DashboardService:
    """Provide a shared :class:`DashboardService` instance.

    Returns:
        A memoized :class:`DashboardService`.
    """
    return DashboardService(storage=get_storage_service())


@lru_cache(maxsize=1)
def get_report_service() -> ReportService:
    """Provide a shared :class:`ReportService` instance.

    Returns:
        A memoized :class:`ReportService`.
    """
    return ReportService(storage=get_storage_service())


@lru_cache(maxsize=1)
def get_settings_service() -> SettingsService:
    """Provide a shared :class:`SettingsService` instance.

    Returns:
        A memoized :class:`SettingsService`.
    """
    return SettingsService(storage=get_storage_service())


# ---------------------------------------------------------------------------
# Authentication / Current User
# ---------------------------------------------------------------------------


async def get_current_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, Any]:
    """Resolve the authenticated user for the current request.

    Prefers the user claims stored on ``request.state.user`` by the
    request-level :class:`AuthenticationMiddleware`.  When middleware is
    not installed (e.g. during tests or a custom app composition), the
    Bearer token is read directly from the ``Authorization`` header and
    verified via :meth:`AuthService.verify_token`.

    Args:
        request: The incoming request.
        auth_service: Injected authentication service.

    Returns:
        A dictionary of decoded user claims (``user_id``, ``username``,
        ``role``).

    Raises:
        AuthenticationError: If no valid bearer token is provided.
    """
    middleware_user: Any = getattr(request.state, "user", None)
    if isinstance(middleware_user, dict):
        return middleware_user

    token: str | None = _extract_bearer_token(request)
    if token is None:
        raise AuthenticationError(
            "Authentication required. Provide a valid bearer token."
        )

    return auth_service.verify_token(token)


# ---------------------------------------------------------------------------
# Compatibility Providers
# ---------------------------------------------------------------------------


def get_db() -> None:
    """Compatibility database dependency.

    VisionOps AI persists to file stores rather than a relational
    database.  This provider is a no-op stub that keeps FastAPI
    dependency signatures stable and testable.

    Returns:
        Always ``None``.
    """
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "get_storage_service",
    "get_auth_service",
    "get_video_service",
    "get_analysis_service",
    "get_analytics_service",
    "get_dashboard_service",
    "get_report_service",
    "get_settings_service",
    "get_current_user",
    "get_db",
]

