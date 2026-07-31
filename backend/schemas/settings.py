"""VisionOps AI — Settings Domain Schemas.

Pydantic v2 schemas for application settings, configuration updates, and
system configuration display. These map directly to the interfaces
exposed by :mod:`backend.services.settings_service` and the settings API.

Contents:
    - :class:`SettingsResponse` — response payload for current settings.
    - :class:`SettingsUpdate` — request body for updating settings.
    - :class:`ConfigurationSchema` — full configuration representation.
    - :class:`SystemInfo` — system-level information.

Validation covers required fields, numeric ranges, enum values, string
lengths, and configuration keys.

Usage:
    from backend.schemas.settings import (
        SettingsResponse, SettingsUpdate, ConfigurationSchema, SystemInfo,
    )
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from pydantic import Field, field_validator

from backend.schemas.common import BaseSchema


# ---------------------------------------------------------------------------
# Settings Response
# ---------------------------------------------------------------------------


class SettingsResponse(BaseSchema):
    """Response payload for current application settings.

    Returns a snapshot of active configuration values that are safe to
    expose to clients (excluding secrets).

    Attributes:
        project_name: Application project name.
        version: Application version.
        environment: Deployment environment name.
        debug: Whether debug mode is enabled.
        api_prefix: API route prefix.
        analytics_enabled: Whether analytics is enabled.
        dashboard_enabled: Whether the dashboard is enabled.
        powerbi_enabled: Whether Power BI integration is enabled.
        bytetrack_enabled: Whether ByteTrack tracking is enabled.
        confidence_threshold: Detection confidence threshold.
        iou_threshold: IoU threshold for NMS.
        device: Inference device.
        log_level: Current logging level.
        updated_at: ISO-8601 timestamp of last settings update.
    """

    project_name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="Application project name.",
        ),
    ]
    version: Annotated[
        str,
        Field(
            min_length=1,
            max_length=20,
            description="Application version.",
            examples=["1.0.0"],
        ),
    ]
    environment: Annotated[
        str,
        Field(
            min_length=1,
            description="Deployment environment.",
            examples=["development"],
        ),
    ]
    debug: Annotated[
        bool,
        Field(default=False, description="Whether debug mode is enabled."),
    ] = False
    api_prefix: Annotated[
        str,
        Field(
            default="/api/v1",
            max_length=50,
            description="API route prefix.",
        ),
    ] = "/api/v1"
    analytics_enabled: Annotated[
        bool,
        Field(
            default=True,
            description="Whether the analytics pipeline is enabled.",
        ),
    ] = True
    dashboard_enabled: Annotated[
        bool,
        Field(
            default=True,
            description="Whether the dashboard is enabled.",
        ),
    ] = True
    powerbi_enabled: Annotated[
        bool,
        Field(
            default=False,
            description="Whether Power BI integration is enabled.",
        ),
    ] = False
    bytetrack_enabled: Annotated[
        bool,
        Field(
            default=True,
            description="Whether ByteTrack tracking is enabled.",
        ),
    ] = True
    confidence_threshold: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.5,
            description="Detection confidence threshold (0.0–1.0).",
        ),
    ] = 0.5
    iou_threshold: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.45,
            description="IoU threshold for NMS (0.0–1.0).",
        ),
    ] = 0.45
    device: Annotated[
        str,
        Field(
            default="auto",
            description="Inference device (cpu, cuda, mps, auto).",
        ),
    ] = "auto"
    log_level: Annotated[
        str,
        Field(
            default="INFO",
            description="Current logging level.",
        ),
    ] = "INFO"
    updated_at: Annotated[
        datetime | None,
        Field(
            default=None,
            description="ISO-8601 timestamp of last update.",
        ),
    ] = None

    @field_validator("project_name", "version", "environment")
    @classmethod
    def _not_empty(cls, value: str) -> str:
        """Reject empty string fields."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("Field must not be empty.")
        return stripped

    @field_validator("confidence_threshold", "iou_threshold")
    @classmethod
    def _validate_threshold(cls, value: float) -> float:
        """Ensure thresholds are in [0.0, 1.0]."""
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"Threshold must be between 0.0 and 1.0, got {value}.")
        return value

    @field_validator("device")
    @classmethod
    def _validate_device(cls, value: str) -> str:
        """Validate inference device."""
        normalized = value.strip().lower()
        valid_devices = {"cpu", "cuda", "mps", "auto"}
        if normalized not in valid_devices:
            raise ValueError(
                f"Invalid device '{value}'. Valid: {', '.join(sorted(valid_devices))}."
            )
        return normalized

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        """Validate log level."""
        normalized = value.strip().upper()
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in valid_levels:
            raise ValueError(
                f"Invalid log_level '{value}'. "
                f"Valid: {', '.join(sorted(valid_levels))}."
            )
        return normalized

    @field_validator("updated_at", mode="before")
    @classmethod
    def _normalize_timestamp(cls, value: datetime | str | None) -> datetime | None:
        """Normalize naive timestamps to timezone-aware UTC."""
        if value is None:
            return None
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            parsed = value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Settings Update
# ---------------------------------------------------------------------------


class SettingsUpdate(BaseSchema):
    """Request body for updating application settings.

    All fields are optional; only provided fields will be updated.

    Attributes:
        project_name: Updated project name.
        debug: Updated debug mode.
        analytics_enabled: Updated analytics toggle.
        dashboard_enabled: Updated dashboard toggle.
        powerbi_enabled: Updated Power BI toggle.
        bytetrack_enabled: Updated ByteTrack toggle.
        confidence_threshold: Updated confidence threshold.
        iou_threshold: Updated IoU threshold.
        device: Updated inference device.
        log_level: Updated logging level.

    Example:
        .. code-block:: json

            {
                "confidence_threshold": 0.6,
                "log_level": "DEBUG",
                "analytics_enabled": true
            }
    """

    project_name: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            max_length=100,
            description="Updated project name.",
        ),
    ] = None
    debug: Annotated[
        bool | None,
        Field(
            default=None,
            description="Updated debug mode.",
        ),
    ] = None
    analytics_enabled: Annotated[
        bool | None,
        Field(
            default=None,
            description="Updated analytics toggle.",
        ),
    ] = None
    dashboard_enabled: Annotated[
        bool | None,
        Field(
            default=None,
            description="Updated dashboard toggle.",
        ),
    ] = None
    powerbi_enabled: Annotated[
        bool | None,
        Field(
            default=None,
            description="Updated Power BI toggle.",
        ),
    ] = None
    bytetrack_enabled: Annotated[
        bool | None,
        Field(
            default=None,
            description="Updated ByteTrack toggle.",
        ),
    ] = None
    confidence_threshold: Annotated[
        float | None,
        Field(
            default=None,
            ge=0.0,
            le=1.0,
            description="Updated confidence threshold (0.0–1.0).",
        ),
    ] = None
    iou_threshold: Annotated[
        float | None,
        Field(
            default=None,
            ge=0.0,
            le=1.0,
            description="Updated IoU threshold (0.0–1.0).",
        ),
    ] = None
    device: Annotated[
        str | None,
        Field(
            default=None,
            description="Updated inference device.",
        ),
    ] = None
    log_level: Annotated[
        str | None,
        Field(
            default=None,
            description="Updated logging level.",
        ),
    ] = None

    @field_validator("project_name")
    @classmethod
    def _project_name_not_empty(cls, value: str | None) -> str | None:
        """Reject empty project name."""
        if value is not None:
            stripped = value.strip()
            if not stripped:
                raise ValueError("project_name must not be empty.")
            return stripped
        return value

    @field_validator("device")
    @classmethod
    def _validate_device(cls, value: str | None) -> str | None:
        """Validate inference device."""
        if value is None:
            return None
        normalized = value.strip().lower()
        valid_devices = {"cpu", "cuda", "mps", "auto"}
        if normalized not in valid_devices:
            raise ValueError(
                f"Invalid device '{value}'. Valid: {', '.join(sorted(valid_devices))}."
            )
        return normalized

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str | None) -> str | None:
        """Validate log level."""
        if value is None:
            return None
        normalized = value.strip().upper()
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in valid_levels:
            raise ValueError(
                f"Invalid log_level '{value}'. "
                f"Valid: {', '.join(sorted(valid_levels))}."
            )
        return normalized


# ---------------------------------------------------------------------------
# Configuration Schema
# ---------------------------------------------------------------------------


class AIConfig(BaseSchema):
    """AI / ML configuration subset.

    Attributes:
        model_path: Path to the YOLO model weights.
        device: Inference device.
        confidence_threshold: Detection confidence threshold.
        iou_threshold: IoU threshold for NMS.
        max_detections: Maximum detections per frame.
        bytetrack_enabled: Whether ByteTrack is enabled.
        bytetrack_match_threshold: ByteTrack match threshold.
        bytetrack_track_buffer: ByteTrack track buffer.
    """

    model_path: Annotated[
        str,
        Field(min_length=1, description="Path to model weights."),
    ]
    device: Annotated[
        str,
        Field(default="auto", description="Inference device."),
    ] = "auto"
    confidence_threshold: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.5,
            description="Confidence threshold.",
        ),
    ] = 0.5
    iou_threshold: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.45,
            description="IoU threshold.",
        ),
    ] = 0.45
    max_detections: Annotated[
        int,
        Field(ge=1, le=10000, default=300, description="Max detections per frame."),
    ] = 300
    bytetrack_enabled: Annotated[
        bool,
        Field(default=True, description="ByteTrack enabled."),
    ] = True
    bytetrack_match_threshold: Annotated[
        float,
        Field(
            ge=0.0,
            le=1.0,
            default=0.8,
            description="ByteTrack match threshold.",
        ),
    ] = 0.8
    bytetrack_track_buffer: Annotated[
        int,
        Field(ge=1, le=300, default=30, description="ByteTrack track buffer."),
    ] = 30


class StorageConfig(BaseSchema):
    """Storage configuration subset.

    Attributes:
        data_folder: Root data directory.
        upload_folder: Video upload directory.
        raw_folder: Raw data directory.
        processed_folder: Processed data directory.
        archive_folder: Archive directory.
        max_upload_size: Maximum upload size in bytes.
    """

    data_folder: Annotated[str, Field(description="Root data directory.")]
    upload_folder: Annotated[str, Field(description="Video upload directory.")]
    raw_folder: Annotated[str, Field(description="Raw data directory.")]
    processed_folder: Annotated[str, Field(description="Processed data directory.")]
    archive_folder: Annotated[str, Field(description="Archive directory.")]
    max_upload_size: Annotated[
        int,
        Field(ge=1, description="Max upload size in bytes."),
    ]


class AnalyticsConfig(BaseSchema):
    """Analytics configuration subset.

    Attributes:
        enabled: Whether analytics is enabled.
        report_refresh_interval: Report refresh interval in seconds.
        powerbi_enabled: Whether Power BI is enabled.
    """

    enabled: Annotated[
        bool,
        Field(default=True, description="Analytics enabled."),
    ] = True
    report_refresh_interval: Annotated[
        int,
        Field(ge=60, le=86400, default=300, description="Refresh interval (s)."),
    ] = 300
    powerbi_enabled: Annotated[
        bool,
        Field(default=False, description="Power BI enabled."),
    ] = False


class ConfigurationSchema(BaseSchema):
    """Full application configuration representation.

    Groups configuration into logical sections: AI, storage, analytics,
    and general application settings.

    Attributes:
        ai: AI / ML configuration.
        storage: Storage configuration.
        analytics: Analytics configuration.
        project_name: Application project name.
        version: Application version.
        environment: Deployment environment.
        debug: Whether debug mode is enabled.
        api_prefix: API route prefix.
        log_level: Current logging level.
    """

    ai: Annotated[AIConfig, Field(description="AI/ML configuration.")]
    storage: Annotated[StorageConfig, Field(description="Storage configuration.")]
    analytics: Annotated[
        AnalyticsConfig,
        Field(description="Analytics configuration."),
    ]
    project_name: Annotated[str, Field(description="Project name.")]
    version: Annotated[str, Field(description="Application version.")]
    environment: Annotated[str, Field(description="Deployment environment.")]
    debug: Annotated[
        bool,
        Field(default=False, description="Debug mode enabled."),
    ] = False
    api_prefix: Annotated[
        str,
        Field(default="/api/v1", description="API route prefix."),
    ] = "/api/v1"
    log_level: Annotated[
        str,
        Field(default="INFO", description="Logging level."),
    ] = "INFO"


# ---------------------------------------------------------------------------
# System Info
# ---------------------------------------------------------------------------


class SystemInfo(BaseSchema):
    """System-level information for diagnostics.

    Attributes:
        python_version: Python runtime version.
        platform: Operating system platform.
        hostname: Machine hostname.
        cpu_count: Number of CPUs.
        memory_total_gb: Total system memory in GB.
        memory_available_gb: Available memory in GB.
        disk_total_gb: Total disk space in GB.
        disk_free_gb: Free disk space in GB.
        uptime_hours: System uptime in hours.
    """

    python_version: Annotated[
        str,
        Field(description="Python runtime version.", examples=["3.13.1"]),
    ]
    platform: Annotated[
        str,
        Field(description="Operating system platform.", examples=["Windows"]),
    ]
    hostname: Annotated[
        str,
        Field(description="Machine hostname."),
    ]
    cpu_count: Annotated[
        int,
        Field(ge=1, description="Number of CPUs."),
    ]
    memory_total_gb: Annotated[
        float,
        Field(ge=0.0, description="Total system memory in GB."),
    ]
    memory_available_gb: Annotated[
        float,
        Field(ge=0.0, description="Available memory in GB."),
    ]
    disk_total_gb: Annotated[
        float,
        Field(ge=0.0, description="Total disk space in GB."),
    ]
    disk_free_gb: Annotated[
        float,
        Field(ge=0.0, description="Free disk space in GB."),
    ]
    uptime_hours: Annotated[
        float,
        Field(ge=0.0, description="System uptime in hours."),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "SettingsResponse",
    "SettingsUpdate",
    "ConfigurationSchema",
    "SystemInfo",
    "AIConfig",
    "StorageConfig",
    "AnalyticsConfig",
]

