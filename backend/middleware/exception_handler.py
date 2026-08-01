"""VisionOps AI — Exception Handling Middleware.

This module centralises error handling for the entire API layer.  It
provides:

- :class:`ExceptionMiddleware` — a ``BaseHTTPMiddleware`` subclass that
  intercepts :class:`~backend.exceptions.VisionOpsError` subclasses and
  any unhandled exception propagating through the application, mapping
  them to a structured :class:`~backend.schemas.response.ErrorResponse`
  envelope.
- :func:`build_error_response` — a reusable helper that converts any
  exception into a :class:`~backend.schemas.response.ErrorResponse`-based
  JSON response.
- :func:`register_exception_handlers` — registers FastAPI-native
  exception handlers for ``HTTPException`` and ``RequestValidationError``
  so those (handled internally by Starlette) also produce the standard
  error envelope.

Every exception is logged.  Internal tracebacks are **never** exposed to
clients — only a generic message is returned for unexpected errors.

Usage::

    from fastapi import FastAPI
    from backend.middleware import (
        ExceptionMiddleware,
        register_exception_handlers,
    )

    app = FastAPI()
    app.add_middleware(ExceptionMiddleware)
    register_exception_handlers(app)

"""

from __future__ import annotations

import logging
import re
from typing import Any, Final, Mapping, Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_409_CONFLICT,
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    HTTP_422_UNPROCESSABLE_CONTENT,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from backend.exceptions import (
    AIError,
    AnalyticsError,
    AuthenticationError,
    StorageError,
    ValidationError,
    VisionOpsError,
)
from backend.exceptions.api_exceptions import (
    APIError,
    AuthorizationError,
    BadRequestError,
    ConflictError,
    InternalAPIError,
    RateLimitError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from backend.schemas.response import ErrorResponse

logger = logging.getLogger("visionops.middleware.exception_handler")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GENERIC_ERROR_CODE: Final[str] = "INTERNAL_SERVER_ERROR"
_GENERIC_ERROR_MESSAGE: Final[str] = (
    "An unexpected internal server error occurred. Please try again later."
)

# Ordered exception → status mapping.  The first ``isinstance`` match wins,
# so more specific exceptions must appear before their base classes.
_STATUS_MAP: Final[tuple[tuple[type[BaseException], int], ...]] = (
    (RateLimitError, HTTP_429_TOO_MANY_REQUESTS),
    (AuthenticationError, HTTP_401_UNAUTHORIZED),
    (AuthorizationError, HTTP_403_FORBIDDEN),
    (ResourceNotFoundError, HTTP_404_NOT_FOUND),
    (ConflictError, HTTP_409_CONFLICT),
    (BadRequestError, HTTP_400_BAD_REQUEST),
    (ValidationError, HTTP_400_BAD_REQUEST),
    (ServiceUnavailableError, HTTP_503_SERVICE_UNAVAILABLE),
    (StorageError, HTTP_500_INTERNAL_SERVER_ERROR),
    (AIError, HTTP_500_INTERNAL_SERVER_ERROR),
    (AnalyticsError, HTTP_500_INTERNAL_SERVER_ERROR),
    (InternalAPIError, HTTP_500_INTERNAL_SERVER_ERROR),
    (APIError, HTTP_400_BAD_REQUEST),
    (VisionOpsError, HTTP_500_INTERNAL_SERVER_ERROR),
)

# Common HTTP status → machine-readable error code map.
_HTTP_ERROR_CODES: Final[Mapping[int, str]] = {
    HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    HTTP_403_FORBIDDEN: "FORBIDDEN",
    HTTP_404_NOT_FOUND: "NOT_FOUND",
    HTTP_405_METHOD_NOT_ALLOWED: "METHOD_NOT_ALLOWED",
    HTTP_415_UNSUPPORTED_MEDIA_TYPE: "UNSUPPORTED_MEDIA_TYPE",
    HTTP_422_UNPROCESSABLE_CONTENT: "VALIDATION_ERROR",
    HTTP_429_TOO_MANY_REQUESTS: "RATE_LIMIT_EXCEEDED",
    HTTP_500_INTERNAL_SERVER_ERROR: "INTERNAL_SERVER_ERROR",
    HTTP_503_SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
}

_ErrorDetail = Mapping[str, object] | Sequence[Mapping[str, object]]


# ---------------------------------------------------------------------------
# Public Helpers
# ---------------------------------------------------------------------------


def build_error_response(
    request: Request,
    exc: BaseException,
    *,
    status_code: int,
    error_code: str | None = None,
    message: str | None = None,
    details: _ErrorDetail | None = None,
) -> JSONResponse:
    """Build a structured :class:`ErrorResponse` JSON response.

    Args:
        request: The originating request (used to propagate the
            correlation id).
        exc: The exception being converted.
        status_code: The HTTP status code for the response.
        error_code: Optional machine-readable error code.  When ``None``,
            it is derived from the exception class name.
        message: Optional human-readable message.  When ``None``, it is
            derived from the exception.
        details: Optional structured error details.

    Returns:
        A ``JSONResponse`` whose body is an ``ErrorResponse`` envelope.
    """
    request_id: str | None = getattr(request.state, "request_id", None)

    payload = ErrorResponse(
        error_code=error_code or _derive_error_code(type(exc)),
        message=message or _message_from_exception(exc),
        details=details,
        request_id=request_id,
    ).model_dump(mode="json")

    return JSONResponse(
        status_code=status_code,
        content=payload,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register FastAPI handlers for built-in exceptions.

    ``HTTPException`` and ``RequestValidationError`` are handled by
    Starlette internally *before* they can reach
    :class:`ExceptionMiddleware`.  Registering handlers here ensures they
    are also converted to the standard ``ErrorResponse`` envelope.

    Args:
        app: The FastAPI application to configure.

    Returns:
        ``None`` — handlers are registered in place on ``app``.
    """

    async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Convert an ``HTTPException`` to an ``ErrorResponse``."""
        code: str = _HTTP_ERROR_CODES.get(
            exc.status_code, _derive_error_code(type(exc))
        )
        return build_error_response(
            request,
            exc,
            status_code=exc.status_code,
            error_code=code,
            message=str(exc.detail),
        )

    async def _validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """Convert a ``RequestValidationError`` to an ``ErrorResponse``."""
        details: list[dict[str, object]] = []
        for error in exc.errors():
            loc = ".".join(str(part) for part in error.get("loc", ()))
            details.append(
                {
                    "field": loc,
                    "message": error.get("msg", ""),
                    "type": error.get("type", ""),
                }
            )
        return build_error_response(
            request,
            exc,
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            error_code="VALIDATION_ERROR",
            message="Request validation failed.",
            details=details,
        )

    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)

    logger.debug(
        "FastAPI exception handlers registered: HTTPException, RequestValidationError"
    )


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class ExceptionMiddleware(BaseHTTPMiddleware):
    """Catch ``VisionOpsError`` and unhandled exceptions in the ASGI stack.

    This middleware wraps the application and converts any exception that
    propagates out of the downstream app into a structured
    :class:`~backend.schemas.response.ErrorResponse`.

    - :class:`~backend.exceptions.VisionOpsError` subclasses are mapped to
      an appropriate HTTP status based on their concrete type.
    - Any other exception is treated as an unexpected server error
      (``500``) and logged with a full traceback for debugging, while the
      client receives only a generic message.

    Attributes:
        app: The underlying ASGI application (Starlette handles dispatch).
        debug: Whether to emit extra debug-level log detail.
    """

    def __init__(self, app: Any, *, debug: bool | None = None) -> None:
        """Initialise the exception handling middleware.

        Args:
            app: The next ASGI application in the stack.
            debug: Optional override for the debug flag.  Defaults to
                ``settings.DEBUG``.
        """
        super().__init__(app)
        from backend.core.config import settings

        self._app = app
        self._debug: bool = settings.DEBUG if debug is None else debug
        logger.debug("ExceptionMiddleware initialised (debug=%s)", self._debug)

    async def dispatch(
        self,
        request: Request,
        call_next: "BaseHTTPMiddleware.CallNext",
    ) -> Response:
        """Dispatch a request, translating exceptions to error responses.

        Args:
            request: The incoming Starlette request.
            call_next: The next middleware/route handler in the chain.

        Returns:
            The downstream response, or a structured error response if an
            exception propagates out of ``call_next``.
        """
        try:
            return await call_next(request)
        except VisionOpsError as exc:
            status_code: int = _resolve_status(exc)
            if status_code >= HTTP_500_INTERNAL_SERVER_ERROR:
                logger.error(
                    "Handled server error: code=%s status=%s message=%s path=%s",
                    _derive_error_code(type(exc)),
                    status_code,
                    exc.message,
                    request.url.path,
                    exc_info=True,
                )
            else:
                logger.warning(
                    "Handled client error: code=%s status=%s message=%s path=%s",
                    _derive_error_code(type(exc)),
                    status_code,
                    exc.message,
                    request.url.path,
                )
            return build_error_response(
                request,
                exc,
                status_code=status_code,
            )
        except HTTPException as exc:
            # Defensive path — HTTPException raised by middleware deeper in
            # the stack (normally handled by FastAPI's internal handlers).
            logger.warning(
                "HTTPException propagated to middleware: status=%s detail=%s path=%s",
                exc.status_code,
                exc.detail,
                request.url.path,
            )
            code: str = _HTTP_ERROR_CODES.get(
                exc.status_code, _derive_error_code(type(exc))
            )
            return build_error_response(
                request,
                exc,
                status_code=exc.status_code,
                error_code=code,
                message=str(exc.detail),
            )
        except Exception as exc:  # noqa: BLE001 - deliberate catch-all
            logger.error(
                "Unhandled exception: type=%s path=%s",
                type(exc).__name__,
                request.url.path,
                exc_info=True,
            )
            return build_error_response(
                request,
                exc,
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                error_code=_GENERIC_ERROR_CODE,
                message=_GENERIC_ERROR_MESSAGE,
            )


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _resolve_status(exc: BaseException) -> int:
    """Resolve the HTTP status code for a VisionOps exception.

    Args:
        exc: The exception instance.

    Returns:
        The most specific matching status code.
    """
    for exc_type, status in _STATUS_MAP:
        if isinstance(exc, exc_type):
            return status
    return HTTP_500_INTERNAL_SERVER_ERROR


def _derive_error_code(exc_type: type[BaseException]) -> str:
    """Derive a machine-readable error code from an exception class name.

    Converts a ``CamelCase`` class name to ``SCREAMING_SNAKE_CASE``.

    Args:
        exc_type: The exception class.

    Returns:
        Uppercased snake-case error code, e.g. ``AUTHENTICATION_ERROR``.
    """
    name: str = exc_type.__name__
    first: str = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    second: str = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", first)
    return second.upper()


def _message_from_exception(exc: BaseException) -> str:
    """Extract a safe human-readable message from an exception.

    VisionOps exceptions expose a safe ``message`` attribute; any other
    exception falls back to a generic message so internal details are
    never leaked to clients.

    Args:
        exc: The exception instance.

    Returns:
        A safe message string.
    """
    if isinstance(exc, VisionOpsError):
        return exc.message or str(exc)
    return _GENERIC_ERROR_MESSAGE


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "ExceptionMiddleware",
    "build_error_response",
    "register_exception_handlers",
]

