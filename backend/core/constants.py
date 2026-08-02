"""VisionOps AI — Core application constants.

This module defines stable, application-wide constants that are shared
across the backend.  The constants are deliberately confined to
low-level, side-effect-free values so that ``import backend.core`` and
``import backend.core.constants`` remain lightweight and never touch the
filesystem.

Values in this module are the canonical defaults for the application
name/version and the logging subsystem.  Runtime configuration lives in
:mod:`backend.core.config`; this module only hosts immutable constants.
"""

from __future__ import annotations

from pathlib import Path

from .config import PROJECT_ROOT

# ---------------------------------------------------------------------------
# Application Identity
# ---------------------------------------------------------------------------

#: Canonical application name used by configuration and reports.
PROJECT_NAME: str = "OptiWare AI"

#: Canonical application version (semver).
VERSION: str = "1.0.0"

#: Short description of the application.
DESCRIPTION: str = (
    "OptiWare AI - Intelligent Warehouse Video Analytics Platform"
)

#: Default URL prefix for all API routes.
API_PREFIX: str = "/api/v1"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

#: Name of the default application logger used by the logging setup.
DEFAULT_LOGGER_NAME: str = "visionops"

#: Default log level used when no level is configured.
DEFAULT_LOG_LEVEL: str = "INFO"

#: Relative path (from ``PROJECT_ROOT``) to the logging YAML file.
LOGGING_CONFIG_PATH: str = "backend/config/logging.yaml"

#: Absolute path to the logging YAML file.
LOGGING_CONFIG_FILE: Path = PROJECT_ROOT / LOGGING_CONFIG_PATH

#: Maximum size of a single log file before rotation (10 MiB).
DEFAULT_LOG_MAX_BYTES: int = 10 * 1024 * 1024

#: Number of rotated log files retained.
DEFAULT_LOG_BACKUP_COUNT: int = 5

# ---------------------------------------------------------------------------
# Fallback Logging Configuration
# ---------------------------------------------------------------------------
# This dictionary is used when the logging YAML is missing or invalid so
# the application always has a functional, deterministic logging setup.

#: Fallback console handler name.
FALLBACK_CONSOLE_HANDLER: str = "console"

#: Fallback app-file handler name.
FALLBACK_APP_FILE_HANDLER: str = "app_file"

#: Fallback error-file handler name.
FALLBACK_ERROR_FILE_HANDLER: str = "error_file"

#: Fallback logging configuration (dictConfig-compatible).
DEFAULT_LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": (
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "concise": {
            "format": "[%(levelname)s] %(name)s: %(message)s",
        },
        "verbose": {
            "format": (
                "%(asctime)s | %(levelname)-8s | %(name)s | "
                "%(pathname)s:%(lineno)d | %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S.%f",
        },
    },
    "handlers": {
        FALLBACK_CONSOLE_HANDLER: {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "concise",
            "stream": "ext://sys.stdout",
        },
        FALLBACK_APP_FILE_HANDLER: {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": "logs/optiware_app.log",
            "maxBytes": DEFAULT_LOG_MAX_BYTES,
            "backupCount": DEFAULT_LOG_BACKUP_COUNT,
            "encoding": "utf-8",
        },
        FALLBACK_ERROR_FILE_HANDLER: {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "verbose",
            "filename": "logs/optiware_error.log",
            "maxBytes": DEFAULT_LOG_MAX_BYTES,
            "backupCount": DEFAULT_LOG_BACKUP_COUNT,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        DEFAULT_LOGGER_NAME: {
            "level": "INFO",
            "handlers": [
                FALLBACK_CONSOLE_HANDLER,
                FALLBACK_APP_FILE_HANDLER,
                FALLBACK_ERROR_FILE_HANDLER,
            ],
            "propagate": False,
        },
    },
    "root": {
        "level": "INFO",
        "handlers": [
            FALLBACK_CONSOLE_HANDLER,
            FALLBACK_APP_FILE_HANDLER,
            FALLBACK_ERROR_FILE_HANDLER,
        ],
        "propagate": True,
    },
}


# ---------------------------------------------------------------------------
# Runtime / Process
# ---------------------------------------------------------------------------

#: Default host for the API server.
DEFAULT_HOST: str = "0.0.0.0"

#: Default port for the API server.
DEFAULT_PORT: int = 8000

#: Default JWT signing algorithm.
DEFAULT_JWT_ALGORITHM: str = "HS256"

#: Default JWT access-token expiry in minutes.
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "PROJECT_NAME",
    "VERSION",
    "DESCRIPTION",
    "API_PREFIX",
    "DEFAULT_LOGGER_NAME",
    "DEFAULT_LOG_LEVEL",
    "LOGGING_CONFIG_PATH",
    "LOGGING_CONFIG_FILE",
    "DEFAULT_LOG_MAX_BYTES",
    "DEFAULT_LOG_BACKUP_COUNT",
    "FALLBACK_CONSOLE_HANDLER",
    "FALLBACK_APP_FILE_HANDLER",
    "FALLBACK_ERROR_FILE_HANDLER",
    "DEFAULT_LOGGING_CONFIG",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "DEFAULT_JWT_ALGORITHM",
    "DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES",
]

