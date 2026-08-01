"""VisionOps AI — Authentication Middleware.

This module provides a fully asynchronous middleware that authenticates
HTTP requests using Bearer tokens.

The middleware:

1. Reads the ``Authorization`` header and extracts the Bearer token.
2. Delegates token verification to the existing
   :class:`~backend.services.auth_service.AuthService.verify_token`
   method — it **never** re-implements JWT parsing.
3. On success, stores the decoded claims on ``request.state.user`` and
   ``request.state.token`` for downstream route handlers and
   dependencies.
4. On failure, raises :class:`~backend.exceptions.AuthenticationError`
   (which the exception-handling middleware converts into a structured
   ``ErrorResponse`` with a ``401`` status).
5. Skips authentication for a configurable set of public/excluded path
   prefixes (e.g. ``/health``, ``/docs``, the login endpoint).

Usage::

    from fastapi import FastAPI
    from backend.middleware import AuthenticationMiddleware

    app = FastAPI()
    app.add_middleware(
        AuthenticationMiddleware,
        public_paths=("/", "/health", "/docs", "/api/v1/auth/login"),
    )

"""

from __future__ import annotations

import logging
from typing import Any, Final

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from backend.exceptions import AuthenticationError
from backend.exceptions.api_exceptions import AuthorizationError
from backend.services.auth_service import AuthService

logger = logging.getLogger("visionops.middleware.authentication")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_AUTHORIZATION_HEADER: Final[str] = "Authorization"
_BEARER_PREFIX: Final[str] = "bearer"
_BEARER_SCHEME_LENGTH: int = len(_BEARER_PREFIX) + 1  # "bearer "

_STATE_USER_ATTR: Final[str] = "user"
_STATE_TOKEN_ATTR: Final[str] = "token"

# Paths that are always treated as public.  The health check, OpenAPI
# docs, and auth endpoints must remain reachable without a token.
_DEFAULT_PUBLIC_PATHS: tuple[str, ...] = (
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)


# ---------------------------------------------------------------------------
# Authentication Middleware
# ---------------------------------------------------------------------------


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Authenticate requests using Bearer tokens via ``AuthService``.

    The middleware performs the following sequence per request:

    - If the request path starts with any configured public path prefix,
      authentication is skipped and the request continues unchanged.
    - Otherwise the ``Authorization`` header is inspected.  A missing or
      malformed header raises :class:`~backend.exceptions.AuthenticationError`.
    - The Bearer token is verified through
      :meth:`AuthService.verify_token
      <backend.services.auth_service.AuthService.verify_token>`, which
      returns a payload dict (``user_id``, ``username``, ``role``).
    - The payload is stored on ``request.state.user`` and the raw token
      on ``request.state.token``.

    Attributes:
        app: The underlying ASGI application (Starlette handles dispatch).
        auth_service: The injected authentication service.
        public_paths: Path prefixes that are exempt from authentication.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        auth_service: AuthService | None = None,
        public_paths: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        """Initialise the authentication middleware.

        Args:
            app: The next ASGI application in the stack.
            auth_service: Optional pre-built ``AuthService``.  When
                ``None``, a default instance is created.
            public_paths: Optional iterable of path prefixes that bypass
                authentication.
        """
        super().__init__(app)
        self._app = app
        self._auth_service: AuthService = auth_service or AuthService()
        self._public_paths: tuple[str, ...] = (
            tuple(public_paths) if public_paths else _DEFAULT_PUBLIC_PATHS
        )
        logger.debug(
            "AuthenticationMiddleware initialised (public_paths=%s)",
            self._public_paths,
        )

    async def dispatch(
        self,
        request: Request,
        call_next: "BaseHTTPMiddleware.CallNext",
    ) -> Response:
        """Dispatch a request, authenticating it unless public.

        Args:
            request: The incoming Starlette request.
            call_next: The next middleware/route handler in the chain.

        Returns:
            The response from downstream once the request has been
            authenticated (or skipped as public).

        Raises:
            AuthenticationError: If no/invalid credentials are provided
                or the token is invalid.
        """
        if self._is_public(request.url.path):
            return await call_next(request)

        token: str | None = self._extract_token(request)
        if token is None:
            logger.warning(
                "Authentication failed: missing bearer token (path=%s)",
                request.url.path,
            )
            raise AuthenticationError(
                "Authentication required. Provide a valid bearer token."
            )

        try:
            payload: dict[str, Any] = self._auth_service.verify_token(token)
        except AuthenticationError:
            logger.warning(
                "Authentication failed: invalid token (path=%s)",
                request.url.path,
            )
            raise
        except AuthorizationError:
            logger.warning(
                "Authentication failed: forbidden (path=%s)",
                request.url.path,
            )
            raise

        setattr(request.state, _STATE_USER_ATTR, payload)
        setattr(request.state, _STATE_TOKEN_ATTR, token)

        logger.debug(
            "Authenticated user_id=%s role=%s path=%s",
            payload.get("user_id", "unknown"),
            payload.get("role", "unknown"),
            request.url.path,
        )

        return await call_next(request)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_public(self, path: str) -> bool:
        """Check whether a request path is exempt from authentication.

        A prefix of ``"/"`` (the root path) only exempts the exact root
        path, not every sub-path.  All other prefixes are matched as
        path prefixes (e.g. ``/health`` matches ``/health`` and
        ``/health/live``).

        Args:
            path: The request path.

        Returns:
            ``True`` if the path is exempt from authentication.
        """
        for prefix in self._public_paths:
            if prefix == "/":
                if path == "/":
                    return True
            elif path.startswith(prefix):
                return True
        return False

    @staticmethod
    def _extract_token(request: Request) -> str | None:
        """Extract a Bearer token from the ``Authorization`` header.

        Args:
            request: The incoming request.

        Returns:
            The token string, or ``None`` if the header is missing,
            malformed, or does not use the Bearer scheme.
        """
        header: str | None = request.headers.get(_AUTHORIZATION_HEADER)
        if not header:
            return None

        parts: list[str] = header.strip().split(" ", maxsplit=1)
        if len(parts) != 2:
            return None

        scheme, token = parts
        if scheme.lower() != _BEARER_PREFIX:
            return None

        token = token.strip()
        return token if token else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["AuthenticationMiddleware"]

