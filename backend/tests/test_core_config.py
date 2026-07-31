"""VisionOps AI — Unit tests for the ``core.config`` module.

Tests the :class:`backend.core.config.Settings` class including:
- Default values
- Environment variable overrides
- Field validators
- Path resolution
- Environment helpers
- Production safeguards
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from backend.core.config import Settings, Environment, PROJECT_ROOT


# ===========================================================================
# Default Values
# ===========================================================================


class TestSettingsDefaults:
    """Verify that Settings initialises with sensible defaults."""

    def test_project_name_default(self):
        """PROJECT_NAME defaults to 'OptiWare AI'."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.PROJECT_NAME == "OptiWare AI"

    def test_version_default(self):
        """VERSION defaults to '1.0.0'."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.VERSION == "1.0.0"

    def test_environment_default(self):
        """ENVIRONMENT defaults to 'development' when not overridden."""
        settings = Settings(_env_file=None)
        assert settings.ENVIRONMENT == "development"

    def test_debug_default(self):
        """DEBUG defaults to True."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.DEBUG is True

    def test_host_default(self):
        """HOST defaults to '0.0.0.0'."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.HOST == "0.0.0.0"

    def test_port_default(self):
        """PORT defaults to 8000."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.PORT == 8000

    def test_api_prefix_default(self):
        """API_PREFIX defaults to '/api/v1'."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.API_PREFIX == "/api/v1"

    def test_secret_key_default(self):
        """SECRET_KEY has a placeholder default."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert "change-me" in settings.SECRET_KEY

    def test_jwt_algorithm_default(self):
        """JWT_ALGORITHM defaults to 'HS256'."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.JWT_ALGORITHM == "HS256"

    def test_access_token_expire_default(self):
        """ACCESS_TOKEN_EXPIRE_MINUTES defaults to 30."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30

    def test_upload_max_size_default(self):
        """UPLOAD_MAX_SIZE defaults to 500 MB."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.UPLOAD_MAX_SIZE == 500 * 1024 * 1024

    def test_confidence_threshold_default(self):
        """CONFIDENCE_THRESHOLD defaults to 0.5."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.CONFIDENCE_THRESHOLD == 0.5

    def test_iou_threshold_default(self):
        """IOU_THRESHOLD defaults to 0.45."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.IOU_THRESHOLD == 0.45

    def test_device_default(self):
        """DEVICE defaults to 'auto'."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.DEVICE == "auto"

    def test_bytetrack_enabled_default(self):
        """BYTETRACK_ENABLED defaults to True."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.BYTETRACK_ENABLED is True

    def test_analytics_enabled_default(self):
        """ANALYTICS_ENABLED defaults to True."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.ANALYTICS_ENABLED is True

    def test_workers_enabled_default(self):
        """WORKERS_ENABLED defaults to True."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.WORKERS_ENABLED is True


# ===========================================================================
# Environment Validation
# ===========================================================================


class TestSettingsEnvironmentValidation:
    """Verify environment string validation."""

    def test_valid_environments(self):
        """All valid environment strings are accepted."""
        for env in ("development", "staging", "production", "testing"):
            settings = Settings(_env_file=None, ENVIRONMENT=env)
            assert settings.ENVIRONMENT == env

    def test_environment_case_insensitive(self):
        """Environment values are case-insensitive."""
        settings = Settings(_env_file=None, ENVIRONMENT="Production")
        assert settings.ENVIRONMENT == "production"

    def test_invalid_environment_raises(self):
        """Invalid environment raises ValueError."""
        with pytest.raises(ValueError, match="Invalid ENVIRONMENT"):
            Settings(_env_file=None, ENVIRONMENT="invalid_env")

    def test_environment_trailing_whitespace(self):
        """Environment with trailing whitespace is normalised."""
        settings = Settings(_env_file=None, ENVIRONMENT="  testing  ")
        assert settings.ENVIRONMENT == "testing"


# ===========================================================================
# Log Level Validation
# ===========================================================================


class TestSettingsLogLevelValidation:
    """Verify log level validation."""

    def test_valid_log_levels(self):
        """All valid log levels are accepted."""
        for level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
            settings = Settings(_env_file=None, ENVIRONMENT="testing", LOG_LEVEL=level)
            assert settings.LOG_LEVEL == level

    def test_log_level_case_insensitive(self):
        """Log level values are case-insensitive."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing", LOG_LEVEL="info")
        assert settings.LOG_LEVEL == "INFO"

    def test_invalid_log_level_raises(self):
        """Invalid log level raises ValueError."""
        with pytest.raises(ValueError, match="Invalid LOG_LEVEL"):
            Settings(_env_file=None, ENVIRONMENT="testing", LOG_LEVEL="TRACE")


# ===========================================================================
# Device Validation
# ===========================================================================


class TestSettingsDeviceValidation:
    """Verify device validation."""

    def test_valid_devices(self):
        """All valid device values are accepted."""
        for device in ("cpu", "cuda", "mps", "auto"):
            settings = Settings(_env_file=None, ENVIRONMENT="testing", DEVICE=device)
            assert settings.DEVICE == device

    def test_device_case_insensitive(self):
        """Device values are case-insensitive."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing", DEVICE="CPU")
        assert settings.DEVICE == "cpu"

    def test_invalid_device_raises(self):
        """Invalid device raises ValueError."""
        with pytest.raises(ValueError, match="Invalid DEVICE"):
            Settings(_env_file=None, ENVIRONMENT="testing", DEVICE="tpu")


# ===========================================================================
# Video Extension Validation
# ===========================================================================


class TestSettingsVideoExtensionValidation:
    """Verify video extension validation."""

    def test_valid_extensions(self):
        """Valid extensions are accepted."""
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="testing",
            ALLOWED_VIDEO_EXTENSIONS=[".mp4", ".avi"],
        )
        assert ".mp4" in settings.ALLOWED_VIDEO_EXTENSIONS
        assert ".avi" in settings.ALLOWED_VIDEO_EXTENSIONS

    def test_extension_dot_added(self):
        """Missing leading dot is automatically added."""
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="testing",
            ALLOWED_VIDEO_EXTENSIONS=["mp4"],
        )
        assert ".mp4" in settings.ALLOWED_VIDEO_EXTENSIONS

    def test_extension_case_normalised(self):
        """Extensions are lowercased."""
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="testing",
            ALLOWED_VIDEO_EXTENSIONS=[".MP4"],
        )
        assert ".mp4" in settings.ALLOWED_VIDEO_EXTENSIONS

    def test_extension_comma_separated_string(self):
        """Comma-separated string is parsed into a list."""
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="testing",
            ALLOWED_VIDEO_EXTENSIONS=".mp4,.avi,.mov",
        )
        assert ".mp4" in settings.ALLOWED_VIDEO_EXTENSIONS
        assert ".mov" in settings.ALLOWED_VIDEO_EXTENSIONS


# ===========================================================================
# Secret Key Validation
# ===========================================================================


class TestSettingsSecretKeyValidation:
    """Verify secret key validation."""

    def test_weak_secret_key_warning(self):
        """Weak secret key logs a warning but does not raise."""
        # Should not raise — only logs a warning
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="testing",
            SECRET_KEY="change-me",
        )
        assert settings.SECRET_KEY == "change-me"

    def test_empty_secret_key_warning(self):
        """Empty secret key logs a warning but does not raise."""
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="testing",
            SECRET_KEY="",
        )
        assert settings.SECRET_KEY == ""


# ===========================================================================
# Allowed Origins
# ===========================================================================


class TestSettingsAllowedOrigins:
    """Verify allowed origins parsing."""

    def test_default_origins(self):
        """Default origins are set."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert "http://localhost:3000" in settings.ALLOWED_ORIGINS

    def test_comma_separated_origins(self):
        """Comma-separated origins string is parsed."""
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="testing",
            ALLOWED_ORIGINS="http://localhost:3000,http://example.com",
        )
        assert "http://example.com" in settings.ALLOWED_ORIGINS


# ===========================================================================
# Environment Helpers
# ===========================================================================


class TestSettingsEnvironmentHelpers:
    """Verify environment helper methods."""

    def test_is_development(self):
        """is_development returns True for development environment."""
        settings = Settings(_env_file=None, ENVIRONMENT="development")
        assert settings.is_development() is True
        assert settings.is_production() is False
        assert settings.is_testing() is False
        assert settings.is_staging() is False

    def test_is_production(self):
        """is_production returns True for production environment."""
        settings = Settings(_env_file=None, ENVIRONMENT="production")
        assert settings.is_production() is True
        assert settings.is_development() is False

    def test_is_testing(self):
        """is_testing returns True for testing environment."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        assert settings.is_testing() is True
        assert settings.is_production() is False

    def test_is_staging(self):
        """is_staging returns True for staging environment."""
        settings = Settings(_env_file=None, ENVIRONMENT="staging")
        assert settings.is_staging() is True
        assert settings.is_production() is False


# ===========================================================================
# Production Safeguards
# ===========================================================================


class TestSettingsProductionSafeguards:
    """Verify production environment safeguards."""

    def test_production_debug_warning(self):
        """Production with debug=True logs a warning but does not raise."""
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="production",
            DEBUG=True,
            SECRET_KEY="a-real-secure-key-that-is-long-enough-32chars!",
        )
        assert settings.DEBUG is True

    def test_production_weak_secret_raises(self):
        """Production with weak secret key raises ValueError."""
        with pytest.raises(ValueError, match="SECRET_KEY"):
            Settings(
                _env_file=None,
                ENVIRONMENT="production",
                SECRET_KEY="change-me-to-a-secure-random-secret-key-in-production",
            )

    def test_production_strong_secret_ok(self):
        """Production with strong secret key is accepted."""
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="production",
            SECRET_KEY="a-strong-256-bit-secret-key-for-production-use!",
        )
        assert settings.is_production() is True


# ===========================================================================
# Path Resolution
# ===========================================================================


class TestSettingsPathResolution:
    """Verify that relative paths are resolved to absolute paths."""

    def test_base_dir_is_path(self):
        """PROJECT_ROOT is a Path object."""
        assert isinstance(PROJECT_ROOT, Path)

    def test_base_dir_exists(self):
        """PROJECT_ROOT points to an existing directory."""
        assert PROJECT_ROOT.exists()

    def test_base_dir_is_absolute(self):
        """PROJECT_ROOT is an absolute path."""
        assert PROJECT_ROOT.is_absolute()

    def test_resolved_data_folder(self):
        """DATA_FOLDER is resolved to an absolute path."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        data_path = Path(settings.DATA_FOLDER)
        assert data_path.is_absolute()

    def test_resolved_upload_folder(self):
        """UPLOAD_FOLDER is resolved to an absolute path."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        upload_path = Path(settings.UPLOAD_FOLDER)
        assert upload_path.is_absolute()


# ===========================================================================
# Model Dump and Display
# ===========================================================================


class TestSettingsDisplay:
    """Verify display and representation methods."""

    def test_repr(self):
        """__repr__ returns a meaningful string."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        rep = repr(settings)
        assert "Settings" in rep
        assert "testing" in rep

    def test_display_summary(self):
        """display_summary returns a multi-line string."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        summary = settings.display_summary()
        assert isinstance(summary, str)
        assert "VisionOps" in summary or "OptiWare" in summary
        assert "=" in summary

    def test_model_dump_contains_keys(self):
        """model_dump returns all configuration keys."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing")
        data = settings.model_dump()
        assert "PROJECT_NAME" in data
        assert "VERSION" in data
        assert "ENVIRONMENT" in data
        assert "SECRET_KEY" in data


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestSettingsEdgeCases:
    """Verify edge-case handling."""

    def test_confidence_threshold_zero(self):
        """CONFIDENCE_THRESHOLD can be 0.0."""
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="testing",
            CONFIDENCE_THRESHOLD=0.0,
        )
        assert settings.CONFIDENCE_THRESHOLD == 0.0

    def test_confidence_threshold_one(self):
        """CONFIDENCE_THRESHOLD can be 1.0."""
        settings = Settings(
            _env_file=None,
            ENVIRONMENT="testing",
            CONFIDENCE_THRESHOLD=1.0,
        )
        assert settings.CONFIDENCE_THRESHOLD == 1.0

    def test_port_min(self):
        """PORT can be 1024."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing", PORT=1024)
        assert settings.PORT == 1024

    def test_port_max(self):
        """PORT can be 65535."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing", PORT=65535)
        assert settings.PORT == 65535

    def test_max_detections_min(self):
        """MAX_DETECTIONS can be 1."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing", MAX_DETECTIONS=1)
        assert settings.MAX_DETECTIONS == 1

    def test_max_detections_max(self):
        """MAX_DETECTIONS can be 10000."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing", MAX_DETECTIONS=10000)
        assert settings.MAX_DETECTIONS == 10000

    def test_debug_false(self):
        """DEBUG can be set to False."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing", DEBUG=False)
        assert settings.DEBUG is False

    def test_is_debug_property(self):
        """is_debug property mirrors DEBUG."""
        settings = Settings(_env_file=None, ENVIRONMENT="testing", DEBUG=True)
        assert settings.is_debug is True
        settings = Settings(_env_file=None, ENVIRONMENT="testing", DEBUG=False)
        assert settings.is_debug is False


# ===========================================================================
# Environment Variable Overrides
# ===========================================================================


class TestSettingsEnvOverrides:
    """Verify that environment variables override defaults."""

    @patch.dict("os.environ", {"PROJECT_NAME": "EnvOverride", "ENVIRONMENT": "testing"}, clear=True)
    def test_env_var_override_project_name(self):
        """Environment variable overrides PROJECT_NAME."""
        import os
        settings = Settings(_env_file=None)
        assert settings.PROJECT_NAME == "EnvOverride"

    @patch.dict("os.environ", {"PORT": "9090", "ENVIRONMENT": "testing"}, clear=True)
    def test_env_var_override_port(self):
        """Environment variable overrides PORT."""
        settings = Settings(_env_file=None)
        assert settings.PORT == 9090

    @patch.dict("os.environ", {"DEBUG": "false", "ENVIRONMENT": "testing"}, clear=True)
    def test_env_var_override_debug(self):
        """Environment variable overrides DEBUG."""
        settings = Settings(_env_file=None)
        assert settings.DEBUG is False

    @patch.dict("os.environ", {"ENVIRONMENT": "staging"}, clear=True)
    def test_env_var_override_environment(self):
        """Environment variable overrides ENVIRONMENT."""
        settings = Settings(_env_file=None)
        assert settings.ENVIRONMENT == "staging"
