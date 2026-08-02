"""VisionOps AI — Authentication API Endpoints.

Exposes login, token refresh, and current-user endpoints over HTTP.
These routes are a thin boundary over
:class:`~backend.services.auth_service.AuthService` and use the existing
authentication schemas from :mod:`backend.schemas.auth`.

Implemented endpoints:
    - ``POST   /auth/login`` — authenticate credentials and issue a token.
    - ``POST   /auth/refresh`` — refresh an existing bearer token.
    - ``GET    /auth/me`` — return the current authenticated user.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from backend.api.dependencies import get_auth_service, get_current_user
from backend.exceptions import AuthenticationError, RequiredFieldError
from backend.schemas.auth import LoginRequest, LoginResponse, TokenResponse
from backend.services import AuthService

# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate a user",
    description=(
        "Validates username/password credentials and returns a bearer "
        "access token together with authenticated user metadata."
    ),
)
async def login(
    payload: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)] = ...,
) -> Any:
    """Authenticate a user and issue an access token.

    Args:
        payload: Validated login request.
        auth_service: Injected authentication service.

    Returns:
        :class:`TokenResponse`-compatible token payload.

    Raises:
        RequiredFieldError: If credentials are missing.
        AuthenticationError: If credentials are invalid (HTTP 401).
    """
    result = auth_service.authenticate_user(
        username=payload.username,
        password=payload.password,
    )
    return result


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an access token",
    description=(
        "Issues a new access token for the bearer token supplied in the "
        "``Authorization`` header."
    ),
)
async def refresh(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)] = ...,
) -> Any:
    """Refresh the current access token.

    Args:
        request: The incoming request (bearer token source).
        auth_service: Injected authentication service.

    Returns:
        :class:`TokenResponse`-compatible token payload.

    Raises:
        RequiredFieldError: If no token is provided.
        AuthenticationError: If the token is invalid (HTTP 401).
    """
    header: str | None = request.headers.get("Authorization")
    if not header:
        raise RequiredFieldError(
            "Bearer token is required for refresh.", field="token"
        )
    parts: list[str] = header.strip().split(" ", maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid authorization header.")
    token: str = parts[1].strip()
    if not token:
        raise RequiredFieldError(
            "Bearer token is required for refresh.", field="token"
        )
    return auth_service.refresh_token(token)


@router.get(
    "/me",
    summary="Get current user",
    description=(
        "Returns the decoded user claims for the authenticated request."
    ),
)
async def me(
    current_user: Annotated[dict[str, Any], Depends(get_current_user)] = ...,
) -> Any:
    """Return the current authenticated user claims.

    Args:
        current_user: Resolved user claims from the auth dependency.

    Returns:
        A dictionary of user claims (``user_id``, ``username``, ``role``).

    Raises:
        AuthenticationError: If the request is not authenticated (401).
    """
    return current_user


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["router"]

