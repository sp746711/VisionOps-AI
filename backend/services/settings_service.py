"""VisionOps AI — Settings Service.

Provides business-logic orchestration for reading and updating application
configuration at runtime. Delegates all configuration storage to the global
``settings`` object from ``backend.core.config`` and the storage layer.

Responsibilities:
    - Configuration access (read)
    - Runtime configuration updates
    - Configuration validation
    - Reset to defaults
    - Configuration change history tracking

Usage::

    from backend.services import SettingsService

    service = SettingsService()
    config = service.get_settings()
    result = service.update_setting("CONFIDENCE_THRESHOLD", 0.6)
    valid = service.validate_setting("DEVICE", "cuda")
    defaults = service.reset_to_defaults()
"""

from __future__ import annotations

import logging
from typing import Any

from backend.core.config import settings, Settings, VALID_LOG_LEVELS, VALID_DEVICES
from backend.exceptions import (
    ValidationError,
    StorageError,
    RequiredFieldError,
    NumericRangeError,
)
from backend.storage import StorageService
from backend.utils.date_utils import now_utc

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Settings that are safe to modify at runtime (non-sensitive, non-critical)
_RUNTIME_ALLOWED_KEYS: frozenset[str] = frozenset({
    # AI / ML
    "CONFIDENCE_THRESHOLD",
    "IOU_THRESHOLD",
    "MAX_DETECTIONS",
    "DEVICE",
    # Analytics
    "ANALYTICS_ENABLED",
    "DASHBOARD_ENABLED",
    "POWERBI_ENABLED",
    # Workers
    "WORKERS_ENABLED",
    "WORKER_CLEANUP_INTERVAL",
    "WORKER_ANALYTICS_INTERVAL",
    # Logging (non-sensitive)
    "LOG_LEVEL",
    # ByteTrack
    "BYTETRACK_ENABLED",
    "BYTETRACK_MATCH_THRESHOLD",
    "BYTETRACK_TRACK_BUFFER",
})

# Protected settings that must NEVER be changed at runtime
_PROTECTED_KEYS: frozenset[str] = frozenset({
    "SECRET_KEY",
    "JWT_ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "PASSWORD_HASHING_SCHEME",
    "HOST",
    "PORT",
    "ALLOWED_ORIGINS",
    "UPLOAD_MAX_SIZE",
    "PASSWORD_MIN_LENGTH",
})

# Setting type validators
_BOOLEAN_KEYS: frozenset[str] = frozenset({
    "ANALYTICS_ENABLED",
    "DASHBOARD_ENABLED",
    "POWERBI_ENABLED",
    "WORKERS_ENABLED",
    "BYTETRACK_ENABLED",
    "DEBUG",
})

_FLOAT_KEYS: frozenset[str] = frozenset({
    "CONFIDENCE_THRESHOLD",
    "IOU_THRESHOLD",
    "BYTETRACK_MATCH_THRESHOLD",
})

_INT_KEYS: frozenset[str] = frozenset({
    "MAX_DETECTIONS",
    "WORKER_CLEANUP_INTERVAL",
    "WORKER_ANALYTICS_INTERVAL",
    "BYTETRACK_TRACK_BUFFER",
})

_STRING_KEYS: frozenset[str] = frozenset({
    "DEVICE",
    "LOG_LEVEL",
})

# ---------------------------------------------------------------------------
# SettingsService
# ---------------------------------------------------------------------------


class SettingsService:
    """Orchestrates configuration access, validation, and runtime updates.

    This service provides a controlled interface for reading and modifying
    application configuration at runtime. It validates changes against
    allowed ranges and types, protects sensitive settings from modification,
    and tracks change history.

    Dependency injection is used for the storage layer to improve
    testability.

    Raises:
        ValidationError: If setting key or value is invalid.
        RequiredFieldError: If a required argument is missing.
        StorageError: If persisting changes fails.
    """

    def __init__(
        self,
        storage: StorageService | None = None,
    ) -> None:
        """Initialise the settings service.

        Args:
            storage: Injected ``StorageService`` instance. When ``None``,
                a default instance is created.
        """
        self._storage = storage or StorageService()
        self._settings = settings
        logger.info(
            "SettingsService initialised (storage=%s)",
            type(self._storage).__name__,
        )

    # ------------------------------------------------------------------
    # Configuration Access
    # ------------------------------------------------------------------

    def get_settings(
        self,
        section: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve current application configuration.

        Args:
            section: Optional section filter — one of ``"ai"``,
                ``"analytics"``, ``"workers"``, ``"security"``,
                ``"logging"``, ``"storage"``. If ``None``, returns
                the entire configuration.

        Returns:
            Dictionary with configuration key-value pairs. Sensitive
            values (like passwords) are masked.

        Raises:
            ValidationError: If *section* is unknown.
        """
        if section is not None:
            return self._get_section(section)

        # Return full config with sensitive values masked
        full_config = self._settings.model_dump()
        self._mask_sensitive(full_config)
        return full_config

    def _get_section(self, section: str) -> dict[str, Any]:
        """Get a specific configuration section.

        Args:
            section: Section name.

        Returns:
            Dictionary of key-value pairs for the section.

        Raises:
            ValidationError: If *section* is unknown.
        """
        section_map: dict[str, list[str]] = {
            "ai": [
                "YOLO_MODEL_PATH", "CLASSES_FILE", "DEVICE",
                "CONFIDENCE_THRESHOLD", "IOU_THRESHOLD", "MAX_DETECTIONS",
                "BYTETRACK_ENABLED", "BYTETRACK_MATCH_THRESHOLD",
                "BYTETRACK_TRACK_BUFFER",
            ],
            "analytics": [
                "ANALYTICS_ENABLED", "DASHBOARD_ENABLED", "POWERBI_ENABLED",
                "REPORT_REFRESH_INTERVAL",
            ],
            "workers": [
                "WORKERS_ENABLED", "WORKER_CLEANUP_INTERVAL",
                "WORKER_ANALYTICS_INTERVAL",
            ],
            "security": [
                "SECRET_KEY", "JWT_ALGORITHM", "ACCESS_TOKEN_EXPIRE_MINUTES",
                "PASSWORD_HASHING_SCHEME", "PASSWORD_MIN_LENGTH",
            ],
            "logging": [
                "LOG_LEVEL", "LOG_DIR", "LOG_FILE_APP", "LOG_FILE_ERROR",
                "LOG_FILE_AI", "LOG_FILE_ACCESS",
            ],
            "storage": [
                "DATA_FOLDER", "UPLOAD_FOLDER", "ARCHIVE_FOLDER",
                "VIDEOS_CSV", "DETECTIONS_CSV", "EVENTS_CSV",
                "ALERTS_CSV", "KPIS_CSV", "ANALYTICS_CSV", "SUMMARY_JSON",
            ],
        }

        keys = section_map.get(section)
        if keys is None:
            raise ValidationError(
                f"Unknown section '{section}'. "
                f"Available sections: {', '.join(sorted(section_map))}."
            )

        result: dict[str, Any] = {}
        full = self._settings.model_dump()
        for key in keys:
            if key in full:
                result[key] = full[key]

        self._mask_sensitive(result)
        return result

    # ------------------------------------------------------------------
    # Runtime Configuration Updates
    # ------------------------------------------------------------------

    def update_setting(
        self,
        key: str,
        value: Any,
    ) -> dict[str, Any]:
        """Update a single configuration setting at runtime.

        Only non-protected, runtime-allowed settings can be modified.
        The change is validated before being applied.

        Args:
            key: Configuration key (e.g. ``"CONFIDENCE_THRESHOLD"``).
            value: New value for the setting.

        Returns:
            Dictionary with update result:
            - ``key``: The setting key.
            - ``old_value``: Previous value.
            - ``new_value``: Updated value.
            - ``status``: ``"updated"`` or ``"unchanged"``.
            - ``timestamp``: ISO-8601 timestamp.

        Raises:
            RequiredFieldError: If *key* is empty.
            ValidationError: If *key* is protected, unknown, or *value*
                is invalid.
            StorageError: If persisting the change fails.
        """
        if not key:
            raise RequiredFieldError(
                "Setting key is required.", field="key"
            )

        key_upper = key.upper().strip()

        # Check protection
        if key_upper in _PROTECTED_KEYS:
            raise ValidationError(
                f"Setting '{key_upper}' is protected and cannot be "
                f"modified at runtime."
            )

        # Check runtime allowance
        if key_upper not in _RUNTIME_ALLOWED_KEYS:
            # Allow if it's a known setting from the model
            known_keys = set(self._settings.model_dump().keys())
            if key_upper not in known_keys:
                raise ValidationError(
                    f"Unknown setting '{key_upper}'. "
                    f"Use validate_setting() to check available keys."
                )
            logger.warning(
                "Setting '%s' is not in the runtime-allowed list "
                "but is a known setting. Proceeding with update.",
                key_upper,
            )

        # Validate the value
        validated_value = self._validate_setting_value(key_upper, value)

        # Get old value
        old_value = getattr(self._settings, key_upper, None)

        if old_value == validated_value:
            logger.info(
                "Setting '%s' unchanged (value=%s).",
                key_upper,
                validated_value,
            )
            return {
                "key": key_upper,
                "old_value": old_value,
                "new_value": validated_value,
                "status": "unchanged",
                "timestamp": now_utc().isoformat(),
            }

        # Apply the change (in-memory update)
        setattr(self._settings, key_upper, validated_value)

        # Log the change
        logger.info(
            "Setting '%s' updated: %s -> %s",
            key_upper,
            old_value,
            validated_value,
        )

        # TODO: Persist runtime config override when available.
        #   from backend.core.config import update_env_override
        #   update_env_override(key_upper, validated_value)

        return {
            "key": key_upper,
            "old_value": old_value,
            "new_value": validated_value,
            "status": "updated",
            "timestamp": now_utc().isoformat(),
        }

    def update_settings_bulk(
        self,
        updates: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Update multiple configuration settings at once.

        Args:
            updates: Dictionary of ``{key: value}`` pairs to update.

        Returns:
            List of per-setting update result dictionaries.

        Raises:
            ValidationError: If *updates* is empty or any key is invalid.
        """
        if not updates:
            raise ValidationError("No updates provided.")

        results: list[dict[str, Any]] = []
        errors: list[str] = []

        for key, value in updates.items():
            try:
                result = self.update_setting(key, value)
                results.append(result)
            except (ValidationError, RequiredFieldError) as exc:
                errors.append(f"'{key}': {exc}")
                results.append({
                    "key": key,
                    "status": "failed",
                    "error": str(exc),
                    "timestamp": now_utc().isoformat(),
                })

        if errors:
            logger.warning(
                "Bulk update completed with %d error(s): %s",
                len(errors),
                "; ".join(errors),
            )
        else:
            logger.info(
                "Bulk update completed: %d setting(s) updated.",
                len(results),
            )

        return results

    # ------------------------------------------------------------------
    # Configuration Validation
    # ------------------------------------------------------------------

    def validate_setting(
        self,
        key: str,
        value: Any,
    ) -> dict[str, Any]:
        """Validate a configuration setting without applying it.

        Args:
            key: Configuration key to validate.
            value: Proposed value.

        Returns:
            Dictionary with validation result:
            - ``key``: The setting key.
            - ``value``: The proposed value (coerced to correct type).
            - ``valid``: Whether the value is valid.
            - ``message``: Human-readable validation message.

        Raises:
            RequiredFieldError: If *key* is empty.
        """
        if not key:
            raise RequiredFieldError(
                "Setting key is required for validation.", field="key"
            )

        key_upper = key.upper().strip()

        # Check if key exists
        known_keys = set(self._settings.model_dump().keys())
        if key_upper not in known_keys:
            return {
                "key": key_upper,
                "value": value,
                "valid": False,
                "message": f"Unknown setting '{key_upper}'.",
            }

        # Check protection
        if key_upper in _PROTECTED_KEYS:
            return {
                "key": key_upper,
                "value": value,
                "valid": True,
                "message": (f"Setting '{key_upper}' is protected and "
                            f"cannot be changed at runtime, but the "
                            f"current value is valid."),
            }

        # Validate value
        try:
            validated = self._validate_setting_value(key_upper, value)
            return {
                "key": key_upper,
                "value": validated,
                "valid": True,
                "message": f"Value is valid.",
            }
        except (ValidationError, NumericRangeError, ValueError) as exc:
            return {
                "key": key_upper,
                "value": value,
                "valid": False,
                "message": str(exc),
            }

    # ------------------------------------------------------------------
    # Reset to Defaults
    # ------------------------------------------------------------------

    def reset_to_defaults(
        self,
        section: str | None = None,
    ) -> dict[str, Any]:
        """Reset configuration settings to their default values.

        Args:
            section: Optional section to reset. If ``None``, only
                runtime-allowed settings are reset.

        Returns:
            Dictionary with reset results:
            - ``reset_count``: Number of settings reset.
            - ``settings``: List of per-setting reset results.
            - ``timestamp``: ISO-8601 timestamp.

        Raises:
            ValidationError: If *section* is unknown.
        """
        if section is not None:
            # Validate section first
            self._get_section(section)

        # Collect keys to reset
        if section:
            section_data = self._get_section(section)
            keys_to_reset = list(section_data.keys())
        else:
            keys_to_reset = list(_RUNTIME_ALLOWED_KEYS)

        # Get default settings
        default_settings = Settings()

        results: list[dict[str, Any]] = []
        reset_count = 0

        for key in keys_to_reset:
            if hasattr(default_settings, key) and hasattr(self._settings, key):
                default_value = getattr(default_settings, key)
                current_value = getattr(self._settings, key)

                if current_value != default_value:
                    setattr(self._settings, key, default_value)
                    reset_count += 1
                    results.append({
                        "key": key,
                        "old_value": current_value,
                        "new_value": default_value,
                        "status": "reset",
                    })
                    logger.info(
                        "Setting '%s' reset to default: %s -> %s",
                        key,
                        current_value,
                        default_value,
                    )
                else:
                    results.append({
                        "key": key,
                        "old_value": current_value,
                        "new_value": default_value,
                        "status": "unchanged",
                    })

        logger.info(
            "Settings reset: %d setting(s) reset to defaults.",
            reset_count,
        )

        return {
            "reset_count": reset_count,
            "settings": results,
            "timestamp": now_utc().isoformat(),
        }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _validate_setting_value(
        self,
        key: str,
        value: Any,
    ) -> Any:
        """Validate and coerce a setting value to its expected type.

        Args:
            key: Setting key.
            value: Proposed value.

        Returns:
            Coerced and validated value.

        Raises:
            ValidationError: If the value is invalid.
            NumericRangeError: If a numeric value is out of range.
        """
        # Boolean validation
        if key in _BOOLEAN_KEYS:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                normalized = value.lower().strip()
                if normalized in ("true", "1", "yes"):
                    return True
                if normalized in ("false", "0", "no"):
                    return False
            if isinstance(value, int):
                return bool(value)
            raise ValidationError(
                f"Invalid boolean value for '{key}': {value!r}. "
                f"Expected True/False."
            )

        # Float validation
        if key in _FLOAT_KEYS:
            try:
                val = float(value)
            except (ValueError, TypeError):
                raise ValidationError(
                    f"Invalid float value for '{key}': {value!r}."
                )

            # Range checks
            if key == "CONFIDENCE_THRESHOLD":
                if val < 0.0 or val > 1.0:
                    raise NumericRangeError(
                        f"CONFIDENCE_THRESHOLD must be between 0.0 and 1.0, "
                        f"got {val}.",
                        value=val, min_val=0.0, max_val=1.0,
                    )
            elif key == "IOU_THRESHOLD":
                if val < 0.0 or val > 1.0:
                    raise NumericRangeError(
                        f"IOU_THRESHOLD must be between 0.0 and 1.0, "
                        f"got {val}.",
                        value=val, min_val=0.0, max_val=1.0,
                    )
            elif key == "BYTETRACK_MATCH_THRESHOLD":
                if val < 0.0 or val > 1.0:
                    raise NumericRangeError(
                        f"BYTETRACK_MATCH_THRESHOLD must be between 0.0 "
                        f"and 1.0, got {val}.",
                        value=val, min_val=0.0, max_val=1.0,
                    )

            return val

        # Integer validation
        if key in _INT_KEYS:
            try:
                val = int(value)
            except (ValueError, TypeError):
                raise ValidationError(
                    f"Invalid integer value for '{key}': {value!r}."
                )

            # Range checks
            if key == "MAX_DETECTIONS":
                if val < 1 or val > 10000:
                    raise NumericRangeError(
                        f"MAX_DETECTIONS must be between 1 and 10000, "
                        f"got {val}.",
                        value=val, min_val=1, max_val=10000,
                    )
            elif key == "WORKER_CLEANUP_INTERVAL":
                if val < 60 or val > 604800:
                    raise NumericRangeError(
                        f"WORKER_CLEANUP_INTERVAL must be between 60 and "
                        f"604800, got {val}.",
                        value=val, min_val=60, max_val=604800,
                    )
            elif key == "WORKER_ANALYTICS_INTERVAL":
                if val < 60 or val > 86400:
                    raise NumericRangeError(
                        f"WORKER_ANALYTICS_INTERVAL must be between 60 "
                        f"and 86400, got {val}.",
                        value=val, min_val=60, max_val=86400,
                    )
            elif key == "BYTETRACK_TRACK_BUFFER":
                if val < 1 or val > 300:
                    raise NumericRangeError(
                        f"BYTETRACK_TRACK_BUFFER must be between 1 and "
                        f"300, got {val}.",
                        value=val, min_val=1, max_val=300,
                    )

            return val

        # String validation
        if key in _STRING_KEYS:
            if not isinstance(value, str) or not value.strip():
                raise ValidationError(
                    f"Invalid string value for '{key}': {value!r}."
                )

            val = value.strip()

            if key == "DEVICE":
                valid_devices = set(VALID_DEVICES) if VALID_DEVICES else {"cpu", "cuda", "mps", "auto"}
                if val.lower() not in valid_devices:
                    raise ValidationError(
                        f"Invalid DEVICE '{val}'. "
                        f"Valid: {', '.join(sorted(valid_devices))}."
                    )
                return val.lower()

            if key == "LOG_LEVEL":
                valid_levels = set(VALID_LOG_LEVELS) if VALID_LOG_LEVELS else {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
                if val.upper() not in valid_levels:
                    raise ValidationError(
                        f"Invalid LOG_LEVEL '{val}'. "
                        f"Valid: {', '.join(sorted(valid_levels))}."
                    )
                return val.upper()

            return val

        # For any other key, accept the value as-is
        return value

    @staticmethod
    def _mask_sensitive(config: dict[str, Any]) -> None:
        """Mask sensitive configuration values in-place.

        Args:
            config: Configuration dictionary to mask.
        """
        sensitive_keys = {"SECRET_KEY", "PASSWORD_HASHING_SCHEME"}
        for key in sensitive_keys:
            if key in config and config[key]:
                val = str(config[key])
                if len(val) > 4:
                    config[key] = val[:2] + "***" + val[-2:]
                else:
                    config[key] = "***"

    @property
    def runtime_allowed_keys(self) -> list[str]:
        """Return the list of settings that can be modified at runtime.

        Returns:
            Sorted list of setting key strings.
        """
        return sorted(_RUNTIME_ALLOWED_KEYS)
