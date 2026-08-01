"""VisionOps AI — CORS Middleware Configuration.

This module provides a single, config-driven helper for registering the
Starlette :class:`~starlette.middleware.cors.CORSMiddleware` on a FastAPI
application.

The project deliberately **reuses** the battle-tested Starlette CORS
implementation rather than re-inventing one.  All values (allowed
origins, methods, headers, credentials) are sourced from the central
configuration singleton (:data:`backend.core.config.settings`), keeping
the middleware layer DRY and consistent with the rest of the backend.

Usage::

    from fastapi import FastAPI
    from backend.middleware import configure_cors

    app = FastAPI()
    configure_cors(app)

"""

from __future__ import annotations

import logging
from typing import Sequence

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings

logger = logging.getLogger("visionops.middleware.cors")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALLOW_CREDENTIALS: bool = True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def configure_cors(
    app: FastAPI,
    *,
    allow_origins: Sequence[str] | None = None,
    allow_methods: Sequence[str] | None = None,
    allow_headers: Sequence[str] | None = None,
    allow_credentials: bool = _ALLOW_CREDENTIALS,
) -> None:
    """Register Starlette CORS middleware on a FastAPI application.

    All parameters default to the values defined in the central settings
    singleton.  Passing explicit values overrides the defaults, which
    keeps the helper flexible for tests while remaining configuration
    driven in production.

    The helper is idempotent with respect to duplicate registration: it
    simply appends a new middleware instance, which is the standard
    Starlette behaviour.  Callers should register CORS **once** during
    application bootstrap.

    Args:
        app: The FastAPI application instance to configure.
        allow_origins: Optional override for ``ALLOWED_ORIGINS``.
        allow_methods: Optional override for ``ALLOWED_METHODS``.
        allow_headers: Optional override for ``ALLOWED_HEADERS``.
        allow_credentials: Whether to allow credentials (default ``True``).

    Returns:
        ``None`` — the middleware is registered in place on ``app``.

    Examples:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> configure_cors(app)
    """
    origins = list(allow_origins if allow_origins is not None else settings.ALLOWED_ORIGINS)
    methods = list(allow_methods if allow_methods is not None else settings.ALLOWED_METHODS)
    headers = list(allow_headers if allow_headers is not None else settings.ALLOWED_HEADERS)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=methods,
        allow_headers=headers,
    )

    logger.debug(
        "CORS middleware registered: origins=%s methods=%s headers=%s credentials=%s",
        origins,
        methods,
        headers,
        allow_credentials,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["configure_cors"]

