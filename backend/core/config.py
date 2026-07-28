"""
OptiWare AI - Central Configuration Module

This module serves as the SINGLE source of truth for all backend configuration.
It uses Pydantic v2 with pydantic-settings for environment-aware configuration
management, pathlib for cross-platform path handling, and follows Clean
Architecture and SOLID principles.

Usage:
    from core.config import settings

    # Access any configuration value
    project_name = settings.PROJECT_NAME
    api_prefix = settings.API_PREFIX
    upload_max_size = settings.UPLOAD_MAX_SIZE
"""

from __future__ import annotations

import logging
import sys
from enum import Enum
from pathlib import Path
from typing import ClassVar, List, Set

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_LOG_LEVELS: Set[str] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
VALID_DEVICES: Set[str] = {"cpu", "cuda", "mps", "auto"}
VALID_VIDEO_EXTENSIONS: Set[str] = {
    ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv",
}
DEFAULT_ALLOWED_METHODS: List[str] = ["*"]
DEFAULT_ALLOWED_HEADERS: List[str] = ["*"]
DEFAULT_API_PREFIX: str = "/api/v1"

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Environment(str, Enum):
    """Application environment options."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


# ---------------------------------------------------------------------------
# Base Directory
# ---------------------------------------------------------------------------

# Determine the project root (two levels up from this file)
# backend/core/config.py -> backend/ -> project root
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _resolve_path(*parts: str) -> Path:
    """Resolve an absolute path relative to the project root.

    Args:
        *parts: Path parts to join relative to the project root.

    Returns:
        Resolved absolute Path object.
    """
    return PROJECT_ROOT.joinpath(*parts).resolve()


def _ensure_directory(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists.

    Returns:
        The same Path object, guaranteed to exist.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def _parse_comma_separated(value: str) -> List[str]:
    """Parse a comma-separated string into a list of stripped strings.

    Args:
        value: Comma-separated string.

    Returns:
        List of stripped string values.
    """
    return [item.strip() for item in value.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Settings Class
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    """Central configuration manager for the OptiWare AI backend.

    All configuration values are loaded from environment variables first,
    falling back to defaults defined in this class. Environment variables
    take precedence over .env files and defaults.

    Every backend module MUST import the global ``settings`` instance
    via::

        from core.config import settings

    Configuration is organized into logical sections for maintainability
    and readability.
    """

    # ------------------------------------------------------------------
    # Model Configuration (Pydantic v2)
    # ------------------------------------------------------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        validate_default=True,
        arbitrary_types_allowed=True,
    )

    # ------------------------------------------------------------------
    # Section 1: Project Information
    # ------------------------------------------------------------------

    PROJECT_NAME: str = Field(
        default="OptiWare AI",
        description="The name of the application project.",
    )
    VERSION: str = Field(
        default="1.0.0",
        description="The current version of the application (semver).",
    )
    DESCRIPTION: str = Field(
        default=(
            "OptiWare AI - Intelligent Warehouse Video Analytics Platform"
        ),
        description="A short description of the application.",
    )
    ENVIRONMENT: str = Field(
        default="development",
        description=(
            "The deployment environment: development, staging, production, "
            "or testing."
        ),
    )
    DEBUG: bool = Field(
        default=True,
        description="Enable or disable debug mode.",
    )

    # ------------------------------------------------------------------
    # Section 2: API Configuration
    # ------------------------------------------------------------------

    HOST: str = Field(
        default="0.0.0.0",
        description="The host address the API server binds to.",
    )
    PORT: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="The port the API server listens on (1024–65535).",
    )
    API_PREFIX: str = Field(
        default=DEFAULT_API_PREFIX,
        description="The URL prefix for all API routes.",
    )

    # ------------------------------------------------------------------
    # Section 3: Security Configuration
    # ------------------------------------------------------------------

    SECRET_KEY: str = Field(
        default="change-me-to-a-secure-random-secret-key-in-production",
        min_length=32,
        description=(
            "Secret key for JWT signing and encryption. "
            "Must be at least 32 characters."
        ),
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="The algorithm used for JWT token signing.",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=1,
        le=525600,
        description=(
            "JWT access token expiration time in minutes (1–525600)."
        ),
    )
    PASSWORD_HASHING_SCHEME: str = Field(
        default="bcrypt",
        description=(
            "Password hashing algorithm: bcrypt, argon2, or pbkdf2."
        ),
    )
    PASSWORD_MIN_LENGTH: int = Field(
        default=8,
        ge=4,
        le=128,
        description="Minimum password length requirement (4–128).",
    )

    # ------------------------------------------------------------------
    # Section 4: CORS Configuration
    # ------------------------------------------------------------------

    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
        ],
        description="List of allowed CORS origins.",
    )
    ALLOWED_METHODS: List[str] = Field(
        default=DEFAULT_ALLOWED_METHODS,
        description="List of allowed HTTP methods for CORS.",
    )
    ALLOWED_HEADERS: List[str] = Field(
        default=DEFAULT_ALLOWED_HEADERS,
        description="List of allowed HTTP headers for CORS.",
    )

    # ------------------------------------------------------------------
    # Section 5: Upload Configuration
    # ------------------------------------------------------------------

    UPLOAD_FOLDER: str = Field(
        default="uploads/videos",
        description=(
            "Directory for uploaded video files (relative to project root)."
        ),
    )
    THUMBNAIL_FOLDER: str = Field(
        default="uploads/thumbnails",
        description=(
            "Directory for generated thumbnails (relative to project root)."
        ),
    )
    UPLOAD_MAX_SIZE: int = Field(
        default=500 * 1024 * 1024,  # 500 MB
        ge=1 * 1024 * 1024,        # Minimum 1 MB
        le=10 * 1024 * 1024 * 1024,  # Maximum 10 GB
        description=(
            "Maximum upload file size in bytes (default 500 MB)."
        ),
    )
    ALLOWED_VIDEO_EXTENSIONS: List[str] = Field(
        default=[
            ".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv",
        ],
        description=(
            "List of allowed video file extensions for upload."
        ),
    )

    # ------------------------------------------------------------------
    # Section 6: Data Storage Configuration
    # ------------------------------------------------------------------

    DATA_FOLDER: str = Field(
        default="data",
        description=(
            "Root directory for all data storage (relative to project root)."
        ),
    )
    RAW_FOLDER: str = Field(
        default="data/raw",
        description="Directory for raw (unprocessed) data files.",
    )
    PROCESSED_FOLDER: str = Field(
        default="data/processed",
        description="Directory for processed/transformed data files.",
    )
    ANALYTICS_FOLDER: str = Field(
        default="data/analytics",
        description="Directory for analytics-related data files.",
    )
    ARCHIVE_FOLDER: str = Field(
        default="data/archive",
        description="Directory for archived/old data files.",
    )

    # ------------------------------------------------------------------
    # Section 7: CSV File Locations
    # ------------------------------------------------------------------

    VIDEOS_CSV: str = Field(
        default="data/videos.csv",
        description="Path to the videos metadata CSV file.",
    )
    DETECTIONS_CSV: str = Field(
        default="data/detections.csv",
        description="Path to the detections data CSV file.",
    )
    EVENTS_CSV: str = Field(
        default="data/events.csv",
        description="Path to the events data CSV file.",
    )
    ALERTS_CSV: str = Field(
        default="data/alerts.csv",
        description="Path to the alerts data CSV file.",
    )
    KPIS_CSV: str = Field(
        default="data/kpis.csv",
        description="Path to the KPIs data CSV file.",
    )
    ANALYTICS_CSV: str = Field(
        default="data/analytics.csv",
        description="Path to the analytics data CSV file.",
    )

    # ------------------------------------------------------------------
    # Section 8: JSON File Locations
    # ------------------------------------------------------------------

    SUMMARY_JSON: str = Field(
        default="data/summary.json",
        description="Path to the summary JSON file.",
    )

    # ------------------------------------------------------------------
    # Section 9: Output Configuration
    # ------------------------------------------------------------------

    ANNOTATED_VIDEOS_DIR: str = Field(
        default="outputs/annotated_videos",
        description="Directory for annotated video outputs.",
    )
    EXTRACTED_FRAMES_DIR: str = Field(
        default="outputs/extracted_frames",
        description="Directory for extracted frame images.",
    )
    DETECTION_IMAGES_DIR: str = Field(
        default="outputs/detection_images",
        description="Directory for detection result images.",
    )
    PREVIEW_IMAGES_DIR: str = Field(
        default="outputs/previews",
        description="Directory for preview/screenshot images.",
    )

    # ------------------------------------------------------------------
    # Section 10: Reports Configuration
    # ------------------------------------------------------------------

    PDF_REPORTS_DIR: str = Field(
        default="reports/pdf",
        description="Directory for generated PDF reports.",
    )
    EXCEL_REPORTS_DIR: str = Field(
        default="reports/excel",
        description="Directory for generated Excel reports.",
    )
    JSON_REPORTS_DIR: str = Field(
        default="reports/json",
        description="Directory for generated JSON reports.",
    )

    # ------------------------------------------------------------------
    # Section 11: AI / ML Configuration
    # ------------------------------------------------------------------

    YOLO_MODEL_PATH: str = Field(
        default="ai/models/detection/yolov8n.pt",
        description="Path to the YOLO model weights file.",
    )
    CLASSES_FILE: str = Field(
        default="ai/models/config/classes.txt",
        description="Path to the YOLO class names file.",
    )
    DEVICE: str = Field(
        default="auto",
        description=(
            "Inference device: 'cpu', 'cuda', 'mps', or 'auto'."
        ),
    )
    CONFIDENCE_THRESHOLD: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "YOLO confidence threshold for detections (0.0–1.0)."
        ),
    )
    IOU_THRESHOLD: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description="YOLO NMS IoU threshold (0.0–1.0).",
    )
    MAX_DETECTIONS: int = Field(
        default=300,
        ge=1,
        le=10000,
        description=(
            "Maximum number of detections per inference frame (1–10000)."
        ),
    )

    # ------------------------------------------------------------------
    # Section 12: ByteTrack Configuration
    # ------------------------------------------------------------------

    BYTETRACK_ENABLED: bool = Field(
        default=True,
        description="Enable or disable ByteTrack object tracking.",
    )
    BYTETRACK_MATCH_THRESHOLD: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description=(
            "ByteTrack matching threshold for association (0.0–1.0)."
        ),
    )
    BYTETRACK_TRACK_BUFFER: int = Field(
        default=30,
        ge=1,
        le=300,
        description=(
            "ByteTrack track buffer size in frames (1–300)."
        ),
    )

    # ------------------------------------------------------------------
    # Section 13: Analytics Configuration
    # ------------------------------------------------------------------

    ANALYTICS_ENABLED: bool = Field(
        default=True,
        description="Enable or disable the analytics processing pipeline.",
    )
    DASHBOARD_ENABLED: bool = Field(
        default=True,
        description="Enable or disable the dashboard API endpoints.",
    )
    POWERBI_ENABLED: bool = Field(
        default=False,
        description="Enable or disable Power BI dataset generation.",
    )
    REPORT_REFRESH_INTERVAL: int = Field(
        default=300,  # 5 minutes
        ge=60,
        le=86400,
        description=(
            "Report data refresh interval in seconds (60–86400)."
        ),
    )

    # ------------------------------------------------------------------
    # Section 14: Logging Configuration
    # ------------------------------------------------------------------

    LOG_DIR: str = Field(
        default="logs",
        description=(
            "Directory for log files (relative to project root)."
        ),
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description=(
            "Logging level: DEBUG, INFO, WARNING, ERROR, or CRITICAL."
        ),
    )
    LOG_FILE_APP: str = Field(
        default="optiware_app.log",
        description="Name of the application log file.",
    )
    LOG_FILE_ERROR: str = Field(
        default="optiware_error.log",
        description="Name of the error log file.",
    )
    LOG_FILE_AI: str = Field(
        default="optiware_ai.log",
        description="Name of the AI inference log file.",
    )
    LOG_FILE_ACCESS: str = Field(
        default="optiware_access.log",
        description="Name of the HTTP access log file.",
    )

    # ------------------------------------------------------------------
    # Section 15: Worker Configuration
    # ------------------------------------------------------------------

    WORKERS_ENABLED: bool = Field(
        default=True,
        description="Enable or disable background worker processes.",
    )
    WORKER_CLEANUP_INTERVAL: int = Field(
        default=3600,  # 1 hour
        ge=60,
        le=86400 * 7,
        description=(
            "Cleanup worker interval in seconds (60–604800)."
        ),
    )
    WORKER_ANALYTICS_INTERVAL: int = Field(
        default=600,  # 10 minutes
        ge=60,
        le=86400,
        description=(
            "Analytics worker processing interval in seconds (60–86400)."
        ),
    )

    # ------------------------------------------------------------------
    # Internal / Computed Properties (not loaded from env)
    # ------------------------------------------------------------------

    _BASE_DIR: ClassVar[Path] = PROJECT_ROOT
    _initialized: bool = False

    # ------------------------------------------------------------------
    # Field Validators
    # ------------------------------------------------------------------

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        """Validate that the environment value is one of the allowed options.

        Args:
            value: The environment string value.

        Returns:
            Lowercased, validated environment string.

        Raises:
            ValueError: If the environment is not a valid option.
        """
        valid_envs = {e.value for e in Environment}
        normalized = value.lower().strip()
        if normalized not in valid_envs:
            msg = (
                f"Invalid ENVIRONMENT '{value}'. "
                f"Must be one of: {', '.join(sorted(valid_envs))}."
            )
            raise ValueError(msg)
        return normalized

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Validate that the log level is a standard logging level.

        Args:
            value: The log level string.

        Returns:
            Uppercased, validated log level string.

        Raises:
            ValueError: If the log level is not valid.
        """
        normalized = value.upper().strip()
        if normalized not in VALID_LOG_LEVELS:
            msg = (
                f"Invalid LOG_LEVEL '{value}'. "
                f"Must be one of: {', '.join(sorted(VALID_LOG_LEVELS))}."
            )
            raise ValueError(msg)
        return normalized

    @field_validator("DEVICE", mode="before")
    @classmethod
    def validate_device(cls, value: str) -> str:
        """Validate that the device is a supported inference device.

        Args:
            value: The device string.

        Returns:
            Lowercased, validated device string.

        Raises:
            ValueError: If the device is not supported.
        """
        normalized = value.lower().strip()
        if normalized not in VALID_DEVICES:
            msg = (
                f"Invalid DEVICE '{value}'. "
                f"Must be one of: {', '.join(sorted(VALID_DEVICES))}."
            )
            raise ValueError(msg)
        return normalized

    @field_validator("ALLOWED_VIDEO_EXTENSIONS", mode="before")
    @classmethod
    def validate_video_extensions(
        cls, value: List[str] | str
    ) -> List[str]:
        """Validate that video extensions have a leading dot and are supported.

        Args:
            value: List of extension strings or comma-separated string.

        Returns:
            List of validated, lowercased extension strings.

        Raises:
            ValueError: If any extension is invalid.
        """
        if isinstance(value, str):
            value = _parse_comma_separated(value)
        validated: List[str] = []
        for ext in value:
            ext = ext.strip().lower()
            if not ext.startswith("."):
                ext = f".{ext}"
            if ext not in VALID_VIDEO_EXTENSIONS:
                logger.warning(
                    "Unrecognized video extension '%s'. Allowed: %s",
                    ext,
                    ", ".join(sorted(VALID_VIDEO_EXTENSIONS)),
                )
            validated.append(ext)
        return validated

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        """Warn if the secret key appears to be a default or placeholder.

        Args:
            value: The secret key string.

        Returns:
            The secret key as-is.
        """
        if value in (
            "change-me",
            "change-me-to-a-secure-random-secret-key-in-production",
            "",
        ):
            logger.warning(
                "SECRET_KEY is set to a weak/default value. "
                "Set a strong, unique SECRET_KEY in production "
                "via environment variable."
            )
        return value

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def validate_allowed_origins(
        cls, value: List[str] | str
    ) -> List[str]:
        """Parse comma-separated origins string into a list if needed.

        Args:
            value: List of origin strings or comma-separated string.

        Returns:
            List of validated origin strings.
        """
        if isinstance(value, str):
            return _parse_comma_separated(value)
        return value

    # ------------------------------------------------------------------
    # Model Validator
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def validate_and_bootstrap(self) -> "Settings":
        """Post-initialization validation and directory bootstrapping.

        This runs after all fields are validated. It:
        - Resolves all relative paths to absolute paths.
        - Ensures all required directories exist.
        - Validates numeric range consistency.
        - Logs the configuration state.

        Returns:
            The validated Settings instance.
        """
        if self._initialized:
            return self

        # Resolve and ensure all managed directories
        self._resolve_and_ensure_directories()

        # Validate runtime consistency
        self._validate_runtime_consistency()

        # Log startup configuration
        environment_label = self.ENVIRONMENT.upper()
        logger.info(
            "OptiWare AI Configuration loaded — "
            "Environment: %s | Debug: %s | Version: %s",
            environment_label,
            self.DEBUG,
            self.VERSION,
        )
        logger.debug(
            "Configuration details: %s", self.model_dump()
        )

        self._initialized = True

        return self

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _resolve_and_ensure_directories(self) -> None:
        """Resolve relative directory paths to absolute and create them."""
        # Data directories
        self._resolve_field_to_abs("DATA_FOLDER")
        self._resolve_field_to_abs("RAW_FOLDER")
        self._resolve_field_to_abs("PROCESSED_FOLDER")
        self._resolve_field_to_abs("ANALYTICS_FOLDER")
        self._resolve_field_to_abs("ARCHIVE_FOLDER")

        # Upload directories
        self._resolve_field_to_abs("UPLOAD_FOLDER")
        self._resolve_field_to_abs("THUMBNAIL_FOLDER")

        # Output directories
        self._resolve_field_to_abs("ANNOTATED_VIDEOS_DIR")
        self._resolve_field_to_abs("EXTRACTED_FRAMES_DIR")
        self._resolve_field_to_abs("DETECTION_IMAGES_DIR")
        self._resolve_field_to_abs("PREVIEW_IMAGES_DIR")

        # Report directories
        self._resolve_field_to_abs("PDF_REPORTS_DIR")
        self._resolve_field_to_abs("EXCEL_REPORTS_DIR")
        self._resolve_field_to_abs("JSON_REPORTS_DIR")

        # AI model paths (directories only)
        self._resolve_field_to_abs("YOLO_MODEL_PATH", is_directory=False)
        self._resolve_field_to_abs("CLASSES_FILE", is_directory=False)

        # CSV file paths (directories only)
        self._resolve_field_to_abs("VIDEOS_CSV", is_directory=False)
        self._resolve_field_to_abs("DETECTIONS_CSV", is_directory=False)
        self._resolve_field_to_abs("EVENTS_CSV", is_directory=False)
        self._resolve_field_to_abs("ALERTS_CSV", is_directory=False)
        self._resolve_field_to_abs("KPIS_CSV", is_directory=False)
        self._resolve_field_to_abs("ANALYTICS_CSV", is_directory=False)

        # JSON file paths
        self._resolve_field_to_abs("SUMMARY_JSON", is_directory=False)

        # Log directory
        self._resolve_field_to_abs("LOG_DIR")

    def _resolve_field_to_abs(
        self, field_name: str, is_directory: bool = True
    ) -> None:
        """Resolve a relative path field to an absolute path.

        If the field value is a relative path, it is resolved relative to
        the project root. Directory fields are created if they do not exist.

        Args:
            field_name: The attribute name on this Settings instance.
            is_directory: If True, the path points to a directory (created).
        """
        current_value = getattr(self, field_name, None)
        if current_value is None:
            return

        path = Path(current_value)
        if not path.is_absolute():
            path = _resolve_path(str(path))

        if is_directory:
            _ensure_directory(path)
        else:
            _ensure_directory(path.parent)

        setattr(self, field_name, str(path))

    def _validate_runtime_consistency(self) -> None:
        """Validate cross-field runtime consistency.

        Raises:
            ValueError: If any consistency check fails.
        """
        if self.CONFIDENCE_THRESHOLD < self.IOU_THRESHOLD:
            logger.warning(
                "CONFIDENCE_THRESHOLD (%.2f) is lower than "
                "IOU_THRESHOLD (%.2f). This may result in very few "
                "detections after NMS.",
                self.CONFIDENCE_THRESHOLD,
                self.IOU_THRESHOLD,
            )

        if self.ENVIRONMENT == Environment.PRODUCTION.value:
            if self.DEBUG:
                logger.warning(
                    "DEBUG mode is enabled in PRODUCTION environment. "
                    "Disable it for security and performance."
                )
            if self.SECRET_KEY in (
                "change-me-to-a-secure-random-secret-key-in-production",
                "change-me",
            ):
                raise ValueError(
                    "SECRET_KEY must be changed from its default "
                    "value in PRODUCTION."
                )

    # ------------------------------------------------------------------
    # Environment Helpers
    # ------------------------------------------------------------------

    def is_development(self) -> bool:
        """Check if the current environment is development.

        Returns:
            True if the environment is 'development'.
        """
        return self.ENVIRONMENT == Environment.DEVELOPMENT.value

    def is_production(self) -> bool:
        """Check if the current environment is production.

        Returns:
            True if the environment is 'production'.
        """
        return self.ENVIRONMENT == Environment.PRODUCTION.value

    def is_testing(self) -> bool:
        """Check if the current environment is testing.

        Returns:
            True if the environment is 'testing'.
        """
        return self.ENVIRONMENT == Environment.TESTING.value

    def is_staging(self) -> bool:
        """Check if the current environment is staging.

        Returns:
            True if the environment is 'staging'.
        """
        return self.ENVIRONMENT == Environment.STAGING.value

    # ------------------------------------------------------------------
    # Convenience Properties
    # ------------------------------------------------------------------

    @property
    def base_dir(self) -> Path:
        """Return the project base directory as a Path."""
        return self._BASE_DIR

    @property
    def resolved_data_dir(self) -> Path:
        """Return the resolved absolute data directory path."""
        return Path(self.DATA_FOLDER)

    @property
    def resolved_upload_dir(self) -> Path:
        """Return the resolved absolute upload directory path."""
        return Path(self.UPLOAD_FOLDER)

    @property
    def resolved_log_dir(self) -> Path:
        """Return the resolved absolute log directory path."""
        return Path(self.LOG_DIR)

    @property
    def is_debug(self) -> bool:
        """Convenience alias for the DEBUG flag."""
        return self.DEBUG

    # ------------------------------------------------------------------
    # Display / Representation
    # ------------------------------------------------------------------

    def display_summary(self) -> str:
        """Return a human-readable summary of the active configuration.

        Returns:
            Multi-line string summarizing key configuration values.
        """
        lines = [
            f"{'=' * 60}",
            f"  OptiWare AI Configuration Summary",
            f"{'=' * 60}",
            f"  Project      : {self.PROJECT_NAME} v{self.VERSION}",
            f"  Environment  : {self.ENVIRONMENT.upper()}",
            f"  Debug Mode   : {self.DEBUG}",
            (
                f"  API          : "
                f"http://{self.HOST}:{self.PORT}{self.API_PREFIX}"
            ),
            f"  Log Level    : {self.LOG_LEVEL}",
            f"  AI Device    : {self.DEVICE}",
            f"  AI Model     : {self.YOLO_MODEL_PATH}",
            (
                f"  Upload Limit : "
                f"{self.UPLOAD_MAX_SIZE / (1024 * 1024):.1f} MB"
            ),
            (
                f"  ByteTrack    : "
                f"{'Enabled' if self.BYTETRACK_ENABLED else 'Disabled'}"
            ),
            (
                f"  Analytics    : "
                f"{'Enabled' if self.ANALYTICS_ENABLED else 'Disabled'}"
            ),
            (
                f"  Workers      : "
                f"{'Enabled' if self.WORKERS_ENABLED else 'Disabled'}"
            ),
            f"{'=' * 60}",
        ]
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"Settings(project={self.PROJECT_NAME}, "
            f"env={self.ENVIRONMENT}, "
            f"debug={self.DEBUG}, "
            f"api={self.HOST}:{self.PORT})"
        )


# ---------------------------------------------------------------------------
# Global Settings Singleton
# ---------------------------------------------------------------------------

settings: Settings = Settings()

# Print configuration summary on import in non-testing environments
if not settings.is_testing():
    print(settings.display_summary(), file=sys.stderr)

__all__ = [
    "Settings",
    "settings",
    "Environment",
    "PROJECT_ROOT",
    "VALID_LOG_LEVELS",
    "VALID_DEVICES",
    "VALID_VIDEO_EXTENSIONS",
]
