"""VisionOps AI — Pydantic v2 Schema Layer.

This package defines all Pydantic v2 schemas used across the VisionOps AI
backend. Every schema is designed for direct use as FastAPI request/response
models and OpenAPI documentation generation.

Modules:
    - :mod:`backend.schemas.common` — shared enums, base class, value objects
    - :mod:`backend.schemas.response` — generic API response envelopes
    - :mod:`backend.schemas.auth` — authentication schemas
    - :mod:`backend.schemas.video` — video domain schemas
    - :mod:`backend.schemas.analysis` — detection analysis schemas
    - :mod:`backend.schemas.analytics` — analytics pipeline schemas
    - :mod:`backend.schemas.dashboard` — dashboard summary schemas
    - :mod:`backend.schemas.report` — report generation schemas
    - :mod:`backend.schemas.settings` — settings/configuration schemas

Usage:
    from backend.schemas import (
        LoginRequest, LoginResponse, TokenResponse,
        VideoUploadRequest, VideoResponse, VideoMetadata,
        AnalysisRequest, AnalysisResponse, DetectionSchema,
        AnalyticsRequest, AnalyticsResponse,
        DashboardSummary, DashboardStatistics,
        ReportRequest, ReportResponse,
        SettingsResponse, SettingsUpdate,
        SuccessResponse, ErrorResponse,
    )
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------

from backend.schemas.common import (
    Severity,
    VideoStatus,
    ReportFormat,
    UserRole,
    PipelineOperation,
    DetectionClass,
    BaseSchema,
    BoundingBox,
    TimeRange,
    PaginationParams,
    DateRangeFilter,
)

# ---------------------------------------------------------------------------
# Response
# ---------------------------------------------------------------------------

from backend.schemas.response import (
    SuccessResponse,
    ErrorResponse,
    PaginatedResponse,
)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

from backend.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)

# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------

from backend.schemas.video import (
    VideoUploadRequest,
    UploadRequest,
    VideoMetadata,
    VideoResponse,
    VideoProcessingRequest,
)

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

from backend.schemas.analysis import (
    DetectionSchema,
    DetectionSummary,
    DetectionStatistics,
    AnalysisRequest,
    AnalysisResponse,
    ConfidenceDistribution,
    ClassCount,
    TimePoint,
)

# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

from backend.schemas.analytics import (
    AnalyticsRequest,
    AnalyticsResponse,
    KPIResponse,
    DashboardMetrics,
    TrendResponse,
    TrendPoint,
    SpoilageMetrics,
    RiskFactor,
    FreshnessMetrics,
)

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

from backend.schemas.dashboard import (
    DashboardSummary,
    DashboardStatistics,
    DashboardStats,
    AlertSummary,
    RecentVideo,
    PerformanceMetrics,
    DashboardResponse,
    VideosByStatus,
    AlertSeverityCount,
    RecentAlert,
)

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

from backend.schemas.report import (
    ReportRequest,
    ReportResponse,
    ReportMetadata,
    ExportRequest,
)

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

from backend.schemas.settings import (
    SettingsResponse,
    SettingsUpdate,
    ConfigurationSchema,
    SystemInfo,
    AIConfig,
    StorageConfig,
    AnalyticsConfig,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # Common
    "Severity",
    "VideoStatus",
    "ReportFormat",
    "UserRole",
    "PipelineOperation",
    "DetectionClass",
    "BaseSchema",
    "BoundingBox",
    "TimeRange",
    "PaginationParams",
    "DateRangeFilter",
    # Response
    "SuccessResponse",
    "ErrorResponse",
    "PaginatedResponse",
    # Auth
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "RegisterResponse",
    "TokenResponse",
    "UserResponse",
    # Video
    "VideoUploadRequest",
    "UploadRequest",
    "VideoMetadata",
    "VideoResponse",
    "VideoProcessingRequest",
    # Analysis
    "DetectionSchema",
    "DetectionSummary",
    "DetectionStatistics",
    "AnalysisRequest",
    "AnalysisResponse",
    "ConfidenceDistribution",
    "ClassCount",
    "TimePoint",
    # Analytics
    "AnalyticsRequest",
    "AnalyticsResponse",
    "KPIResponse",
    "DashboardMetrics",
    "TrendResponse",
    "TrendPoint",
    "SpoilageMetrics",
    "RiskFactor",
    "FreshnessMetrics",
    # Dashboard
    "DashboardSummary",
    "DashboardStatistics",
    "DashboardStats",
    "AlertSummary",
    "RecentVideo",
    "PerformanceMetrics",
    "DashboardResponse",
    "VideosByStatus",
    "AlertSeverityCount",
    "RecentAlert",
    # Report
    "ReportRequest",
    "ReportResponse",
    "ReportMetadata",
    "ExportRequest",
    # Settings
    "SettingsResponse",
    "SettingsUpdate",
    "ConfigurationSchema",
    "SystemInfo",
    "AIConfig",
    "StorageConfig",
    "AnalyticsConfig",
]
