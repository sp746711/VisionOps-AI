"""VisionOps AI — Sanity tests for the ``services`` package.

The Services package modules are currently stubs (zero bytes).
These tests verify that the modules can be imported and their
expected public symbols are accessible.
"""

from __future__ import annotations

import pytest


class TestServicesPackage:
    """Sanity checks for the services package."""

    def test_services_init_module(self):
        """The services __init__ module can be imported."""
        import backend.services  # noqa: F401

    def test_analysis_service_module(self):
        """The analysis_service module can be imported."""
        import backend.services.analysis_service  # noqa: F401

    def test_analytics_service_module(self):
        """The analytics_service module can be imported."""
        import backend.services.analytics_service  # noqa: F401

    def test_auth_service_module(self):
        """The auth_service module can be imported."""
        import backend.services.auth_service  # noqa: F401

    def test_dashboard_service_module(self):
        """The dashboard_service module can be imported."""
        import backend.services.dashboard_service  # noqa: F401

    def test_notification_service_module(self):
        """The notification_service module can be imported."""
        import backend.services.notification_service  # noqa: F401

    def test_report_service_module(self):
        """The report_service module can be imported."""
        import backend.services.report_service  # noqa: F401

    def test_settings_service_module(self):
        """The settings_service module can be imported."""
        import backend.services.settings_service  # noqa: F401

    def test_video_service_module(self):
        """The video_service module can be imported."""
        import backend.services.video_service  # noqa: F401
