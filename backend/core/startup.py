"""VisionOps AI — Application lifecycle/bootstrap helpers.

This module provides explicit, async lifecycle functions used by the
FastAPI application lifespan (:mod:`backend.main`) and tests:

* :func:`startup_event` — one-time application startup (initialises
  storage, marks services ready).
* :func:`shutdown_event` — graceful application shutdown.

Importing this module performs **no** startup work and creates **no**
files or directories.  Initialisation happens only when the functions
are explicitly awaited.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("visionops.core.startup")

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

#: Tracks whether startup has already been run (guards against duplicate
#: initialisation and makes the helpers idempotent).
_started: bool = False

#: Stores the resolved storage directories returned by
#: :class:`~backend.storage.StorageService.initialize`.
_startup_result: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def startup_event() -> dict[str, Any]:
    """Perform one-time application startup.

    This helper initialises the storage layer (ensuring managed
    directories exist) and records the result.  It is idempotent: calling
    it more than once does not re-initialise storage.

    Returns:
        A dictionary containing the startup status.  When storage
        initialisation succeeds, it includes the resolved managed
        directories; otherwise it reports the failure.

    Raises:
        RuntimeError: If storage initialisation fails unexpectedly.
    """
    global _started, _startup_result

    if _started:
        logger.info("Startup already performed — skipping.")
        return {
            "status": "already_started",
            "started": True,
            "storage": _startup_result,
        }

    logger.info("Running VisionOps AI startup event…")

    try:
        # Resolve the storage facade across supported import contexts.
        try:
            from ..storage import StorageService
        except ImportError:  # pragma: no cover - import context
            try:
                from backend.storage import StorageService  # type: ignore
            except ImportError:  # pragma: no cover - top-level packages
                from storage import StorageService  # type: ignore

        storage = StorageService()
        dirs = storage.initialize()
        _startup_result = {str(k): str(v) for k, v in dirs.items()}
    except Exception as exc:  # noqa: BLE001 - lifecycle errors are reported
        logger.exception("Startup storage initialisation failed: %s", exc)
        raise RuntimeError(f"Startup failed: {exc}") from exc

    _started = True

    logger.info(
        "Startup complete — %d managed directories.",
        len(_startup_result or {}),
    )
    return {
        "status": "started",
        "started": True,
        "storage": _startup_result,
    }


async def shutdown_event() -> dict[str, Any]:
    """Perform graceful application shutdown.

    Currently a lightweight hook that records shutdown state.  It is
    idempotent and never raises.

    Returns:
        A dictionary with the shutdown status.
    """
    global _started

    logger.info("Running VisionOps AI shutdown event…")

    _started = False

    logger.info("Shutdown complete.")
    return {
        "status": "shutdown",
        "started": _started,
    }


def is_started() -> bool:
    """Return whether the startup event has been run.

    Returns:
        ``True`` if :func:`startup_event` has completed successfully.
    """
    return _started


def get_startup_result() -> dict[str, Any] | None:
    """Return the result of the most recent startup.

    Returns:
        The startup result dictionary, or ``None`` if startup has not
        completed.
    """
    return _startup_result


def reset_startup() -> None:
    """Reset the startup state (primarily for tests).

    Returns:
        ``None``
    """
    global _started, _startup_result
    _started = False
    _startup_result = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "startup_event",
    "shutdown_event",
    "is_started",
    "get_startup_result",
    "reset_startup",
]

