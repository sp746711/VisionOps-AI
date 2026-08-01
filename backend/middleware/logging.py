"""VisionOps AI — Request Logging & Correlation Middleware.

This module provides two complementary, fully asynchronous middleware
classes:

- :class:`RequestLoggingMiddleware` — emits structured access-log lines
  for every request (method, path, status, client IP, correlation id,
  and optional duration) and records the correlation id on
  ``request.state``.
- The correlation id is generated via the shared
  :func:`~backend.utils.id_generator.generate_correlation_id` helper and
  is returned to the client as the ``X-Request-ID`` response header.

The correlation id is stored on ``request.state.request_id`` so that
downstream middleware (e.g. timing and exception handling) can include it
in logs and error envelopes without re-deriving it.

Usage::

    from fastapi import FastAPI
    from backend.middleware import RequestLoggingMiddleware

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

"""

from __future__ import annotations

import logging
from typing import Final

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from backend.utils.id_generator import generate_correlation_id

logger = logging.getLogger("visionops.middleware.logging")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REQUEST_ID_HEADER: Final[str] = "X-Request-ID"
_STATE_ATTR: Final[str] = "request_id"

# List of paths that should not be logged (e.g. health checks / metrics).
# Kept minimal — override via ``excluded_paths`` when constructing the
# middleware if a deployment needs additional exclusions.
_DEFAULT_EXCLUDED_PATHS: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Request Logging Middleware
# ---------------------------------------------------------------------------


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with a correlation id and structured data.

    The middleware:

    1. Generates (or reuses) a correlation id from the ``X-Request-ID``
       request header.
    2. Stores it on ``request.state.request_id``.
    3. Adds the ``X-Request-ID`` response header.
    4. Logs a single-line, structured message after the response has been
       produced, including the method, path, status code, client IP, and
       correlation id.

    If the downstream timing middleware has already recorded a
    ``process_time`` on ``request.state``, the duration is included in the
    log line as well.

    Attributes:
        app: The underlying ASGI application (Starlette handles dispatch).
        excluded_paths: Request paths that should not produce log lines.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        excluded_paths: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        """Initialise the request logging middleware.

        Args:
            app: The next ASGI application in the stack.
            excluded_paths: Optional iterable of path prefixes to skip.
        """
        super().__init__(app)
        self._app = app
        self._excluded_paths: tuple[str, ...] = (
            tuple(excluded_paths) if excluded_paths else _DEFAULT_EXCLUDED_PATHS
        )
        logger.debug("RequestLoggingMiddleware initialised")

    async def dispatch(
        self,
        request: Request,
        call_next: "BaseHTTPMiddleware.CallNext",
    ) -> Response:
        """Dispatch a request, assigning a correlation id and logging it.

        Args:
            request: The incoming Starlette request.
            call_next: The next middleware/route handler in the chain.

        Returns:
            The response from downstream, with the ``X-Request-ID``
            header added.
        """
        request_id: str = self._resolve_request_id(request)
        setattr(request.state, _STATE_ATTR, request_id)

        path: str = request.url.path
        is_excluded: bool = self._is_excluded(path)

        if not is_excluded:
            logger.info(
                "request_start method=%s path=%s client=%s request_id=%s",
                request.method,
                path,
                self._client_ip(request),
                request_id,
            )

        response: Response = await call_next(request)

        response.headers[_REQUEST_ID_HEADER] = request_id

        if not is_excluded:
            process_time: float | None = getattr(
                request.state, "process_time", None
            )
            duration_ms: float = (
                process_time * 1000.0 if process_time is not None else 0.0
            )
            logger.info(
                "request_end method=%s path=%s status=%s duration_ms=%.2f "
                "client=%s request_id=%s",
                request.method,
                path,
                response.status_code,
                duration_ms,
                self._client_ip(request),
                request_id,
            )

        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_excluded(self, path: str) -> bool:
        """Check whether a path prefix should be excluded from logging.

        Args:
            path: The request path.

        Returns:
            ``True`` if the path starts with any configured prefix.
        """
        return any(path.startswith(prefix) for prefix in self._excluded_paths)

    @staticmethod
    def _resolve_request_id(request: Request) -> str:
        """Return the incoming correlation id or generate a new one.

        Args:
            request: The incoming request.

        Returns:
            A non-empty correlation id string.
        """
        incoming: str | None = request.headers.get(_REQUEST_ID_HEADER)
        if incoming and incoming.strip():
            return incoming.strip()
        return generate_correlation_id()

    @staticmethod
    def _client_ip(request: Request) -> str:
        """Extract the client IP address from a request.

        Falls back to the client host if present, otherwise ``"unknown"``.

        Args:
            request: The incoming request.

        Returns:
            The client IP/host string.
        """
        if request.client is not None and request.client.host:
            return request.client.host
        return "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "RequestLoggingMiddleware",
    "generate_correlation_id",
]

