"""VisionOps AI — Central logging configuration.

This module provides the single entry point for configuring Python's
``logging`` subsystem across the backend.  It loads ``logging.yaml``
from ``backend/config/logging.yaml`` when available, and falls back to a
safe inline configuration otherwise.

Design guarantees:

* **Explicit** — no logging setup happens at import time.  Call
  :func:`setup_logging` during application bootstrap.
* **Idempotent** — repeated calls do not duplicate handlers.
* **Safe** — a missing/invalid YAML file yields a controlled fallback
  configuration; the setup never raises.
* **No secrets** — log messages never include secret values.
* **No side effects at import** — file/directory creation happens only
  when ``dictConfig`` is applied by an explicit call.

Usage::

    from backend.core.logging import setup_logging

    setup_logging()
"""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path
from typing import Any, Final

from .config import settings
from .constants import (
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOGGING_CONFIG,
    LOGGING_CONFIG_FILE,
)

logger = logging.getLogger("visionops.core.logging")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Sentinel used to track whether logging has already been configured.
_INITIALIZED_FLAG: Final[str] = "_visionops_logging_configured"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_configured() -> bool:
    """Check whether logging has already been initialised."""
    root = logging.getLogger()
    return bool(getattr(root, _INITIALIZED_FLAG, False))


def _mark_configured() -> None:
    """Mark the root logger as configured to make setup idempotent."""
    root = logging.getLogger()
    setattr(root, _INITIALIZED_FLAG, True)


def _dedupe_handlers() -> None:
    """Remove duplicate file handlers from the root logger.

    Re-applying ``dictConfig`` can attach the same file handler twice.
    This helper keeps the root logger clean by dropping file handlers
    that reference the same base filename.
    """
    root = logging.getLogger()
    seen: set[str] = set()
    retained: list[logging.Handler] = []

    for handler in list(root.handlers):
        name = getattr(handler, "baseFilename", None)
        if name is None:
            retained.append(handler)
            continue
        key = str(name)
        if key in seen:
            handler.close()
            continue
        seen.add(key)
        retained.append(handler)

    root.handlers[:] = retained


def _load_yaml_config(config_path: Path) -> dict[str, Any] | None:
    """Load a logging configuration dictionary from a YAML file.

    Args:
        config_path: Absolute path to the YAML configuration.

    Returns:
        A ``dictConfig``-compatible dictionary, or ``None`` when the file
        is missing, malformed, or does not contain a dictionary.
    """
    try:
        import yaml  # Lazy import — no hard dependency at import time.
    except ImportError:
        logger.debug("PyYAML is not available; using inline logging config.")
        return None

    try:
        if not config_path.is_file():
            logger.debug("Logging config not found: %s", config_path)
            return None
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        logger.warning(
            "Failed to load logging config '%s': %s. Using fallback.",
            config_path,
            exc,
        )
        return None

    if not isinstance(raw, dict):
        logger.warning(
            "Logging config '%s' is not a mapping. Using fallback.",
            config_path,
        )
        return None

    return raw


def _apply_config(config: dict[str, Any], *, level: str | None = None) -> None:
    """Apply a ``dictConfig``-compatible configuration dictionary.

    Args:
        config: The configuration dictionary.
        level: Optional root/logger level override.
    """
    # Ensure the log directory exists before file handlers are created.
    log_dir = Path(settings.LOG_DIR)
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("Could not create log directory '%s': %s", log_dir, exc)

    # Resolve relative file paths in handlers against the project root so
    # logging works regardless of the current working directory.
    for handler_cfg in config.get("handlers", {}).values():
        filename = handler_cfg.get("filename")
        if isinstance(filename, str) and not Path(filename).is_absolute():
            resolved = Path(settings.base_dir) / filename
            handler_cfg["filename"] = str(resolved)

    if level:
        config.setdefault("root", {})["level"] = level
        for logger_cfg in config.get("loggers", {}).values():
            logger_cfg["level"] = level

    logging.config.dictConfig(config)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def setup_logging(
    config_path: str | Path | None = None,
    *,
    level: str | None = None,
    force: bool = False,
) -> bool:
    """Configure the application logging subsystem.

    This function is idempotent: calling it more than once is a no-op
    unless *force* is ``True``.

    Args:
        config_path: Optional override for the logging YAML path.  When
            ``None``, :data:`~backend.core.constants.LOGGING_CONFIG_FILE`
            is used.
        level: Optional log-level override applied to the root logger and
            all configured loggers.
        force: If ``True``, re-apply the configuration even if logging
            was already initialised.

    Returns:
        ``True`` if logging was (re)configured, ``False`` if the call
        was a no-op because logging was already initialised.

    Examples:
        >>> setup_logging()
        True
        >>> setup_logging()  # idempotent no-op
        False
    """
    if _is_configured() and not force:
        return False

    resolved_path = (
        Path(config_path)
        if config_path is not None
        else LOGGING_CONFIG_FILE
    )

    config = _load_yaml_config(resolved_path) or DEFAULT_LOGGING_CONFIG

    try:
        _apply_config(config, level=level)
    except Exception as exc:  # noqa: BLE001 - logging must never crash the app
        logging.basicConfig(level=level or DEFAULT_LOG_LEVEL)
        logger.warning(
            "Logging configuration failed (%s); using basicConfig fallback.",
            exc,
        )

    _dedupe_handlers()
    _mark_configured()

    logger.info(
        "Logging initialised (config=%s, level=%s).",
        resolved_path,
        level or DEFAULT_LOG_LEVEL,
    )
    return True


def reset_logging() -> None:
    """Reset the logging configuration flag.

    This is primarily useful for tests that need to re-run
    :func:`setup_logging` in the same process.

    Returns:
        ``None``
    """
    root = logging.getLogger()
    if hasattr(root, _INITIALIZED_FLAG):
        delattr(root, _INITIALIZED_FLAG)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["setup_logging", "reset_logging"]

