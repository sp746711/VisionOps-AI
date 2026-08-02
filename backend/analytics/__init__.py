"""VisionOps AI — Analytics Package.

This package implements the analytics/data-processing layer for VisionOps
AI.  It transforms raw and processed VisionOps data into cleaned
analytics datasets, aggregated detection statistics, time-based metrics,
KPI-ready datasets, dashboard-ready datasets, Power BI-ready datasets and
report-ready analytical summaries.

Data flow::

    Storage / Detection / Event / KPI data
                    ↓
            backend/analytics
                    ↓
    AnalyticsService / DashboardService / ReportService
                    ↓
    Dashboard / Reports / Power BI

The package provides:

* :class:`AnalyticsLoader` — loads analytics source records through the
  existing storage abstraction.
* :class:`DataCleaner` — cleans and normalises analytical records.
* :class:`DataTransformer` — converts cleaned records into analytical
  structures.
* :class:`Aggregator` — reusable analytical aggregation.
* :class:`DashboardDatasetBuilder` — builds dashboard-ready datasets.
* :class:`PowerBIDatasetBuilder` / :class:`PowerBIDataset` — builds
  Power BI-ready tabular datasets.
* :class:`ReportDataGenerator` — builds report-ready analytical data.
* :class:`AnalyticsPipeline` — high-level pipeline/facade orchestrating
  the full workflow.

Usage::

    from backend.analytics import AnalyticsPipeline

    pipeline = AnalyticsPipeline()
    result = pipeline.run(filters={"video_ids": ["vid_001"]})
"""

from __future__ import annotations

from backend.analytics.aggregator import Aggregator
from backend.analytics.cleaner import CleaningResult, DataCleaner
from backend.analytics.dashboard_dataset import DashboardDatasetBuilder
from backend.analytics.loader import (
    AnalyticsFilters,
    AnalyticsLoader,
    AnalyticsSourceData,
)
from backend.analytics.pipeline import AnalyticsPipeline, PipelineOutput
from backend.analytics.powerbi_dataset import (
    PowerBIDataset,
    PowerBIDatasetBuilder,
    TABLE_COLUMNS,
)
from backend.analytics.report_generator import ReportDataGenerator
from backend.analytics.transformer import DataTransformer, TransformResult

__all__ = [
    # Loader
    "AnalyticsLoader",
    "AnalyticsFilters",
    "AnalyticsSourceData",
    # Cleaner
    "DataCleaner",
    "CleaningResult",
    # Transformer
    "DataTransformer",
    "TransformResult",
    # Aggregator
    "Aggregator",
    # Dataset builders
    "DashboardDatasetBuilder",
    "PowerBIDatasetBuilder",
    "PowerBIDataset",
    "TABLE_COLUMNS",
    # Report data
    "ReportDataGenerator",
    # Pipeline
    "AnalyticsPipeline",
    "PipelineOutput",
]

