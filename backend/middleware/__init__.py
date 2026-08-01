"""VisionOps AI — Middleware Layer.

This package contains the FastAPI/Starlette middleware components for the
VisionOps AI backend.  Each module implements a single cross-cutting
concern and follows the project's Clean Architecture and SOLID principles.

Modules:
    - :mod:`~backend.middleware.cors` — config-driven CORS registration.
    - :mod:`~backend.middleware.timing` — request timing and
      ``X-Process-Time`` header.
    - :mod:`~backend.middleware.logging` — structured request logging and
      correlation id propagation (``X-Request-ID``).
    - :mod:`~backend.middleware.authentication` — Bearer-token
      authentication via ``AuthService``.
    - :mod:`~backend.middleware.exception_handler` — central exception
      handling producing structured ``ErrorResponse`` envelopes.

Middleware ordering (outermost → innermost) follows dependency:

    logging → exception → authentication → timing

Because Starlette's ``add_middleware`` applies middleware LIFO (the
last one added becomes the outermost), register them in **reverse**
order::

    app.add_middleware(RequestTimingMiddleware)      # innermost
    app.add_middleware(AuthenticationMiddleware)
    app.add_middleware(ExceptionMiddleware)
    app.add_middleware(RequestLoggingMiddleware)     # outermost

Logging should be outermost so a correlation id is available for all
downstream layers — including error responses.  Exception handling
sits just inside logging so it can translate any ``VisionOpsError``
raised by deeper middleware or route handlers into a consistent error
envelope.  Authentication sits inside exception handling so auth
failures become structured ``401`` responses carrying the correlation
id.

Usage::

    from fastapi import FastAPI
    from backend.middleware import (
        configure_cors,
        RequestLoggingMiddleware,
        RequestTimingMiddleware,
        AuthenticationMiddleware,
        ExceptionMiddleware,
        register_exception_handlers,
    )

    app = FastAPI()

    configure_cors(app)
    register_exception_handlers(app)

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(AuthenticationMiddleware)
    app.add_middleware(ExceptionMiddleware)

"""

from __future__ import annotations

from backend.middleware.authentication import AuthenticationMiddleware
from backend.middleware.cors import configure_cors
from backend.middleware.exception_handler import (
    ExceptionMiddleware,
    build_error_response,
    register_exception_handlers,
)
from backend.middleware.logging import (
    RequestLoggingMiddleware,
    generate_correlation_id,
)
from backend.middleware.timing import RequestTimingMiddleware

__all__ = [
    # CORS
    "configure_cors",
    # Logging
    "RequestLoggingMiddleware",
    "generate_correlation_id",
    # Timing
    "RequestTimingMiddleware",
    # Authentication
    "AuthenticationMiddleware",
    # Exception handling
    "ExceptionMiddleware",
    "build_error_response",
    "register_exception_handlers",
]

