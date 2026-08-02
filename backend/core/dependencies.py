"""VisionOps AI — Core dependency providers.

This module provides lightweight, low-level dependency providers shared
across the backend.  It intentionally does **not** import FastAPI or any
higher application layer.  The providers here are plain Python callables
that return configuration-derived values; API-layer providers live in
:mod:`backend.api.dependencies`.

Importing this module has no side effects beyond the already-initialised
:data:`~backend.core.config.settings` singleton.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import settings
from .constants import (
    DEFAULT_LOG_LEVEL,
    LOGGING_CONFIG_FILE,
    LOGGING_CONFIG_PATH,
)

# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


def get_settings() -> Any:
    """Return the application configuration singleton.

    Returns:
        The shared :class:`~backend.core.config.Settings` instance.
    """
    return settings


def get_project_root() -> Path:
    """Return the absolute project root directory.

    Returns:
        A :class:`~pathlib.Path` pointing to the project root.
    """
    return settings.base_dir


def get_log_level() -> str:
    """Return the configured logging level.

    Returns:
        A standard logging level name (e.g. ``"INFO"``).
    """
    return getattr(settings, "LOG_LEVEL", DEFAULT_LOG_LEVEL)


def get_logging_config_path() -> Path:
    """Return the absolute path to the logging YAML file.

    Returns:
        The :data:`~backend.core.constants.LOGGING_CONFIG_FILE` path.
    """
    return LOGGING_CONFIG_FILE


def get_logging_config_relative_path() -> str:
    """Return the relative path to the logging YAML file.

    Returns:
        The :data:`~backend.core.constants.LOGGING_CONFIG_PATH` string.
    """
    return LOGGING_CONFIG_PATH


def get_core_dependencies() -> dict[str, Any]:
    """Return a summary dictionary of the core dependency providers.

    Useful for diagnostics, health checks, and startup reporting.

    Returns:
        A dictionary mapping provider names to their resolved values.
    """
    return {
        "project_root": str(get_project_root()),
        "log_level": get_log_level(),
        "logging_config_path": str(get_logging_config_path()),
        "logging_config_relative_path": get_logging_config_relative_path(),
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "get_settings",
    "get_project_root",
    "get_log_level",
    "get_logging_config_path",
    "get_logging_config_relative_path",
    "get_core_dependencies",
]

