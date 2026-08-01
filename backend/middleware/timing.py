"""VisionOps AI — Request Timing Middleware.

This module provides a fully asynchronous middleware that measures the
processing time of every HTTP request using the project's
:class:`~backend.utils.timer.Timer` utility.

The measured duration is:

- Attached to the response as the ``X-Process-Time`` header (seconds).
- Stored on ``request.state`` as ``process_time`` for downstream
  middleware / exception handlers to reuse.
- Logged as a structured access-log line with the method, path, and
  status code.

The middleware never blocks the event loop and is safe to register via
:meth:`FastAPI.add_middleware`.

Usage::

    from fastapi import FastAPI
    from backend.middleware import RequestTimingMiddleware

    app = FastAPI()
    app.add_middleware(RequestTimingMiddleware)

"""

from __future__ import annotations

import logging
import time
from typing import Final

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

logger = logging.getLogger("visionops.middleware.timing")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PROCESS_TIME_HEADER: Final[str] = "X-Process-Time"
_STATE_ATTR: Final[str] = "process_time"


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Measure and log the processing time of every HTTP request.

    Timing is performed with :class:`time.perf_counter` (via the shared
    :class:`~backend.utils.timer.Timer` helper) to obtain a monotonic,
    high-resolution measurement.  The elapsed duration is exposed both as
    an ``X-Process-Time`` response header and as
    ``request.state.process_time`` (in seconds).

    The middleware logs every request at ``INFO`` level using a
    structured, single-line message that includes the HTTP method,
    request path, resulting status code, client address, and duration —
    enabling straight-forward correlation with the access log.

    Attributes:
        app: The underlying ASGI application (Starlette handles dispatch).
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialise the timing middleware.

        Args:
            app: The next ASGI application in the stack.
        """
        super().__init__(app)
        self._app = app
        logger.debug("RequestTimingMiddleware initialised")

    async def dispatch(
        self,
        request: Request,
        call_next: "BaseHTTPMiddleware.CallNext",
    ) -> Response:
        """Dispatch a request through the application, timing it.

        Args:
            request: The incoming Starlette request.
            call_next: The next middleware/route handler in the chain.

        Returns:
            The response produced by the downstream application, with the
            ``X-Process-Time`` header added.
        """
        start_ns: float = time.perf_counter()
        request_id: str | None = getattr(request.state, "request_id", None)

        try:
            response: Response = await call_next(request)
        except Exception:
            # Re-raise to let the exception middleware handle it, but
            # ensure the duration is still recorded on state.
            elapsed: float = time.perf_counter() - start_ns
            setattr(request.state, _STATE_ATTR, elapsed)
            self._log_access(
                method=request.method,
                path=request.url.path,
                status_code=0,
                duration=elapsed,
                client=request.client.host if request.client else "unknown",
                request_id=request_id,
            )
            raise

        elapsed = time.perf_counter() - start_ns
        setattr(request.state, _STATE_ATTR, elapsed)
        response.headers[_PROCESS_TIME_HEADER] = f"{elapsed:.6f}"

        self._log_access(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=elapsed,
            client=request.client.host if request.client else "unknown",
            request_id=request_id,
        )

        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _log_access(
        *,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        client: str,
        request_id: str | None,
    ) -> None:
        """Emit a structured access-log line for a single request.

        Args:
            method: The HTTP method (e.g. ``"GET"``).
            path: The request path.
            status_code: The HTTP status code (``0`` on unhandled errors).
            duration: Elapsed time in seconds.
            client: The client IP address.
            request_id: Optional correlation id for the request.
        """
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%.2f client=%s request_id=%s",
            method,
            path,
            status_code,
            duration * 1000.0,
            client,
            request_id or "-",
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["RequestTimingMiddleware"]

