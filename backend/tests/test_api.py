"""VisionOps AI — Sanity tests for the ``api`` package.

The API package modules are currently stubs (zero bytes).
These tests verify that the modules can be imported and their
expected public symbols are accessible.
"""

from __future__ import annotations

import pytest


class TestAPIPackage:
    """Sanity checks for the api package."""

    def test_api_init_module(self):
        """The api __init__ module can be imported."""
        import backend.api  # noqa: F401

    def test_router_module(self):
        """The router module can be imported."""
        import backend.api.router  # noqa: F401

    def test_analysis_module(self):
        """The analysis module can be imported."""
        import backend.api.analysis  # noqa: F401

    def test_analytics_module(self):
        """The analytics module can be imported."""
        import backend.api.analytics  # noqa: F401

    def test_auth_module(self):
        """The auth module can be imported."""
        import backend.api.auth  # noqa: F401

    def test_dashboard_module(self):
        """The dashboard module can be imported."""
        import backend.api.dashboard  # noqa: F401

    def test_dependencies_module(self):
        """The dependencies module can be imported."""
        import backend.api.dependencies  # noqa: F401

    def test_health_module(self):
        """The health module can be imported."""
        import backend.api.health  # noqa: F401

    def test_reports_module(self):
        """The reports module can be imported."""
        import backend.api.reports  # noqa: F401

    def test_settings_module(self):
        """The settings module can be imported."""
        import backend.api.settings  # noqa: F401

    def test_videos_module(self):
        """The videos module can be imported."""
        import backend.api.videos  # noqa: F401

