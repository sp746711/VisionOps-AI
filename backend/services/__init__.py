"""VisionOps AI — Services Package.

This package contains the business-logic service layer for the VisionOps AI
backend. Each service encapsulates a domain concern and delegates low-level
operations to ``backend.storage``, ``backend.analytics``, ``backend.ai``,
``backend.business``, ``backend.reports``, ``backend.utils``, and
``backend.exceptions``.

Services MUST NOT contain:
- FastAPI endpoints
- HTTP requests
- Route definitions
- Database models
- YOLO inference implementation
- ByteTrack implementation
- Low-level CSV/JSON operations
- Direct filesystem utilities
- Power BI implementation
- Thread creation
- Background worker loops
- Business rules that belong in ``backend/business``

Usage::

    from backend.services import (
        VideoProcessingService,
        AnalysisService,
        AnalyticsService,
        AuthService,
        DashboardService,
        NotificationService,
        ReportService,
        SettingsService,
    )

    video_service = VideoProcessingService()
    analysis_service = AnalysisService()
    analytics_service = AnalyticsService()
    auth_service = AuthService()
    dashboard_service = DashboardService()
    notification_service = NotificationService()
    report_service = ReportService()
    settings_service = SettingsService()
"""

from __future__ import annotations

from backend.services.analysis_service import AnalysisService
from backend.services.analytics_service import AnalyticsService
from backend.services.auth_service import AuthService
from backend.services.dashboard_service import DashboardService
from backend.services.notification_service import NotificationService
from backend.services.report_service import ReportService
from backend.services.settings_service import SettingsService
from backend.services.video_service import VideoProcessingService

__all__ = [
    "AnalysisService",
    "AnalyticsService",
    "AuthService",
    "DashboardService",
    "NotificationService",
    "ReportService",
    "SettingsService",
    "VideoProcessingService",
]

