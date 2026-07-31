"""VisionOps AI — Analytics exception classes.

These exceptions cover data aggregation, transformation,
reporting, and dashboard-related operations.
"""

from .base_exception import VisionOpsError


class AnalyticsError(VisionOpsError):
    """Base exception for all analytics operations."""

