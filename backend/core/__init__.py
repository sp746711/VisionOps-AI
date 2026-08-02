"""VisionOps AI — Core shared infrastructure.

The ``core`` package provides the low-level, application-independent
building blocks used by the rest of the backend:

* :mod:`~backend.core.config` — central configuration singleton.
* :mod:`~backend.core.constants` — application-wide constants.
* :mod:`~backend.core.logging` — explicit, idempotent logging setup.
* :mod:`~backend.core.security` — JWT/password primitives.
* :mod:`~backend.core.dependencies` — low-level dependency providers.
* :mod:`~backend.core.startup` — explicit application lifecycle helpers.

Importing this package is lightweight and has **no side effects**: it
does not create files/directories, configure logging, start services, or
load models.  All initialisation is deferred to explicit functions
(:func:`~backend.core.logging.setup_logging`,
:func:`~backend.core.startup.startup_event`, etc.).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Lightweight public API
# ---------------------------------------------------------------------------
# Only import modules that are guaranteed side-effect-free and cheap to
# import.  ``security`` and ``startup`` are intentionally not eagerly
# imported here to keep ``import backend.core`` lightweight (they import
# optional dependencies and application services, respectively).

from .config import (
    Environment,
    PROJECT_ROOT,
    Settings,
    settings,
)
from .constants import (
    API_PREFIX,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOGGER_NAME,
    DESCRIPTION,
    LOGGING_CONFIG_FILE,
    LOGGING_CONFIG_PATH,
    PROJECT_NAME,
    VERSION,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # config
    "Settings",
    "settings",
    "Environment",
    "PROJECT_ROOT",
    # constants
    "PROJECT_NAME",
    "VERSION",
    "DESCRIPTION",
    "API_PREFIX",
    "DEFAULT_LOGGER_NAME",
    "DEFAULT_LOG_LEVEL",
    "LOGGING_CONFIG_PATH",
    "LOGGING_CONFIG_FILE",
]

