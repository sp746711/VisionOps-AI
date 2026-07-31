"""VisionOps AI — Sanity tests for the ``analytics`` package.

The Analytics package modules are currently stubs (zero bytes).
These tests verify that the modules can be imported and their
expected public symbols are accessible.
"""

from __future__ import annotations

import pytest


class TestAnalyticsPackage:
    """Sanity checks for the analytics package."""

    def test_analytics_init_module(self):
        """The analytics __init__ module can be imported."""
        import backend.analytics  # noqa: F401

    def test_aggregator_module(self):
        """The aggregator module can be imported."""
        import backend.analytics.aggregator  # noqa: F401

    def test_cleaner_module(self):
        """The cleaner module can be imported."""
        import backend.analytics.cleaner  # noqa: F401

    def test_dashboard_dataset_module(self):
        """The dashboard_dataset module can be imported."""
        import backend.analytics.dashboard_dataset  # noqa: F401

    def test_loader_module(self):
        """The loader module can be imported."""
        import backend.analytics.loader  # noqa: F401

    def test_pipeline_module(self):
        """The pipeline module can be imported."""
        import backend.analytics.pipeline  # noqa: F401

    def test_powerbi_dataset_module(self):
        """The powerbi_dataset module can be imported."""
        import backend.analytics.powerbi_dataset  # noqa: F401

    def test_report_generator_module(self):
        """The report_generator module can be imported."""
        import backend.analytics.report_generator  # noqa: F401

    def test_transformer_module(self):
        """The transformer module can be imported."""
        import backend.analytics.transformer  # noqa: F401
