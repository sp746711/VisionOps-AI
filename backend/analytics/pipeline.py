"""VisionOps AI — Analytics Pipeline.

This module implements the high-level analytics pipeline/facade.  It
orchestrates the complete analytics workflow for the
:class:`~backend.services.analytics_service.AnalyticsService`:

    Storage/data sources
            ↓
    AnalyticsLoader
            ↓
    DataCleaner
            ↓
    DataTransformer
            ↓
    Aggregator
            ↓
    Dataset builders (dashboard / report / Power BI)
            ↓
    Analytics result

Design rules:

* Every component is dependency-injectable so tests can use mocked
  storage and/or mocked pipeline stages.
* Store data is loaded exactly once per run (no repeated reloads).
* The pipeline never performs AI inference, never implements FastAPI
  endpoints, and never duplicates the storage layer.
* Empty source data is a legitimate, first-class outcome; genuine
  processing failures propagate as
  :class:`~backend.exceptions.AnalyticsError`.
* Output is deterministic for the same source records and configuration.

Usage::

    from backend.analytics import AnalyticsPipeline

    pipeline = AnalyticsPipeline()
    result = pipeline.run(filters={"video_ids": ["vid_001"]})
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from backend.analytics.aggregator import Aggregator
from backend.analytics.cleaner import CleaningResult, DataCleaner
from backend.analytics.dashboard_dataset import DashboardDatasetBuilder
from backend.analytics.loader import AnalyticsLoader, AnalyticsSourceData
from backend.analytics.powerbi_dataset import PowerBIDataset, PowerBIDatasetBuilder
from backend.analytics.report_generator import ReportDataGenerator
from backend.analytics.transformer import DataTransformer, TransformResult
from backend.exceptions import AnalyticsError
from backend.utils.date_utils import now_utc

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public data containers
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class PipelineOutput:
    """Result of a full analytics pipeline run.

    Attributes:
        status: Pipeline status (``"completed"``).
        filters: Filters applied during the run.
        source: Loaded source data (see :class:`AnalyticsSourceData`).
        cleaning: Per-store cleaning results.
        transformed: Transformed analytical records.
        aggregates: Aggregated metrics.
        dashboard_dataset: Dashboard-ready dataset (or ``None``).
        report_data: Report-ready data (or ``None``).
        powerbi_dataset: Power BI dataset (or ``None``).
        generated_at: UTC ISO-8601 completion timestamp.
    """

    status: str = "completed"
    filters: dict[str, Any] = field(default_factory=dict)
    source: AnalyticsSourceData = field(default_factory=AnalyticsSourceData)
    cleaning: dict[str, CleaningResult] = field(default_factory=dict)
    transformed: TransformResult = field(default_factory=TransformResult)
    aggregates: dict[str, Any] = field(default_factory=dict)
    dashboard_dataset: dict[str, Any] | None = None
    report_data: dict[str, Any] | None = None
    powerbi_dataset: PowerBIDataset | None = None
    generated_at: str = field(default_factory=lambda: now_utc().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dictionary representation of the pipeline output.

        Returns:
            Dictionary with every output section.  Power BI tables are
            exposed under ``powerbi`` (from
            :meth:`PowerBIDataset.to_dict`).
        """
        cleaning: dict[str, Any] = {}
        for store_name, result in self.cleaning.items():
            cleaning[store_name] = {
                "total_input": result.total_input,
                "accepted": result.accepted,
                "rejected": result.rejected,
                "rejected_reasons": dict(result.rejected_reasons),
            }

        return {
            "status": self.status,
            "filters": dict(self.filters),
            "source": self.source.to_dict(),
            "cleaning": cleaning,
            "transformed": self.transformed.to_dict(),
            "aggregates": self.aggregates,
            "dashboard_dataset": self.dashboard_dataset,
            "report_data": self.report_data,
            "powerbi": self.powerbi_dataset.to_dict()
            if self.powerbi_dataset is not None
            else None,
            "generated_at": self.generated_at,
        }


# ---------------------------------------------------------------------------
# AnalyticsPipeline
# ---------------------------------------------------------------------------


class AnalyticsPipeline:
    """High-level analytics pipeline/facade.

    Args:
        loader: Optional injected :class:`AnalyticsLoader`.
        cleaner: Optional injected :class:`DataCleaner`.
        transformer: Optional injected :class:`DataTransformer`.
        aggregator: Optional injected :class:`Aggregator`.
        dashboard_builder: Optional injected
            :class:`DashboardDatasetBuilder`.
        report_generator: Optional injected
            :class:`ReportDataGenerator`.
        powerbi_builder: Optional injected
            :class:`PowerBIDatasetBuilder`.
    """

    def __init__(
        self,
        *,
        loader: AnalyticsLoader | None = None,
        cleaner: DataCleaner | None = None,
        transformer: DataTransformer | None = None,
        aggregator: Aggregator | None = None,
        dashboard_builder: DashboardDatasetBuilder | None = None,
        report_generator: ReportDataGenerator | None = None,
        powerbi_builder: PowerBIDatasetBuilder | None = None,
    ) -> None:
        """Initialise the analytics pipeline."""
        self._loader = loader or AnalyticsLoader()
        self._cleaner = cleaner or DataCleaner()
        self._transformer = transformer or DataTransformer()
        self._aggregator = aggregator or Aggregator()
        self._dashboard_builder = dashboard_builder or DashboardDatasetBuilder(
            aggregator=self._aggregator,
            transformer=self._transformer,
        )
        self._report_generator = report_generator or ReportDataGenerator(
            aggregator=self._aggregator,
            transformer=self._transformer,
        )
        self._powerbi_builder = powerbi_builder or PowerBIDatasetBuilder()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        filters: dict[str, Any] | None = None,
        *,
        include_dashboard: bool = True,
        include_report: bool = True,
        include_powerbi: bool = True,
    ) -> PipelineOutput:
        """Run the full analytics pipeline.

        Args:
            filters: Optional filter parameters (``video_ids``,
                ``date_from``, ``date_to``).
            include_dashboard: Build the dashboard dataset when ``True``
                (default).
            include_report: Build the report data when ``True``
                (default).
            include_powerbi: Build the Power BI dataset when ``True``
                (default).

        Returns:
            A :class:`PipelineOutput` with every requested section.

        Raises:
            AnalyticsError: If any pipeline stage fails.
        """
        filters = filters or {}
        logger.info(
            "Analytics pipeline run started (filters=%s, dashboard=%s, "
            "report=%s, powerbi=%s).",
            filters,
            include_dashboard,
            include_report,
            include_powerbi,
        )

        try:
            source = self._loader.load_all(filters)
            return self._process(
                source=source,
                filters=filters,
                include_dashboard=include_dashboard,
                include_report=include_report,
                include_powerbi=include_powerbi,
            )
        except AnalyticsError:
            raise
        except Exception as exc:  # pragma: no cover - defensive boundary
            raise AnalyticsError(
                f"Analytics pipeline failed: {exc}"
            ) from exc

    def process(
        self,
        data: AnalyticsSourceData,
        *,
        include_dashboard: bool = True,
        include_report: bool = True,
        include_powerbi: bool = True,
    ) -> PipelineOutput:
        """Run the pipeline over pre-loaded source data.

        This is useful when callers already hold the source records (for
        example from mocked storage or tests).

        Args:
            data: Loaded analytics source data.
            include_dashboard: Build the dashboard dataset when ``True``
                (default).
            include_report: Build the report data when ``True``
                (default).
            include_powerbi: Build the Power BI dataset when ``True``
                (default).

        Returns:
            A :class:`PipelineOutput`.
        """
        return self._process(
            source=data,
            filters={},
            include_dashboard=include_dashboard,
            include_report=include_report,
            include_powerbi=include_powerbi,
        )

    # ------------------------------------------------------------------
    # Stage helpers (individually callable for testing)
    # ------------------------------------------------------------------

    def load(
        self,
        filters: dict[str, Any] | None = None,
    ) -> AnalyticsSourceData:
        """Load analytics source data through the storage layer."""
        return self._loader.load_all(filters)

    def clean(
        self,
        data: AnalyticsSourceData,
    ) -> dict[str, CleaningResult]:
        """Clean loaded source data store-by-store."""
        return self._cleaner.clean_all(data.to_dict())

    def transform(
        self,
        cleaning: dict[str, CleaningResult],
    ) -> TransformResult:
        """Transform cleaned records into analytical structures.

        Args:
            cleaning: Per-store cleaning results.

        Returns:
            A :class:`TransformResult`.
        """
        return TransformResult(
            videos=self._transformer.transform_videos(
                cleaning["videos"].cleaned
            ),
            detections=self._transformer.transform_detections(
                cleaning["detections"].cleaned
            ),
            events=self._transformer.transform_events(
                cleaning["events"].cleaned
            ),
            alerts=self._transformer.transform_alerts(
                cleaning["alerts"].cleaned
            ),
            kpis=self._transformer.transform_kpis(
                cleaning["kpis"].cleaned
            ),
            analytics=self._transformer.transform_analytics(
                cleaning["analytics"].cleaned
            ),
        )

    def aggregate(
        self,
        transformed: TransformResult,
    ) -> dict[str, Any]:
        """Aggregate transformed records into metrics.

        Args:
            transformed: Transformed analytical records.

        Returns:
            Dictionary with ``detections``, ``events``, ``alerts`` and
            ``kpis`` aggregate sections.
        """
        detections = transformed.detections
        return {
            "detections": {
                "total": self._aggregator.total_detections(detections),
                "by_class": self._aggregator.detections_by_class(
                    detections
                ),
                "by_video": self._aggregator.detections_by_video(
                    detections
                ),
                "confidence": self._aggregator.confidence_statistics(
                    detections
                ),
                "confidence_distribution": (
                    self._aggregator.confidence_distribution(detections)
                ),
                "tracking": self._transformer.compute_tracking_stats(
                    detections
                ),
                "per_video_summaries": self._aggregator.per_video_summaries(
                    detections
                ),
                "over_time": self._aggregator.detections_over_time(
                    detections
                ),
            },
            "events": self._aggregator.event_counts(transformed.events),
            "alerts": self._aggregator.alert_counts(transformed.alerts),
            "kpis": self._aggregator.kpi_summary(transformed.kpis),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process(
        self,
        *,
        source: AnalyticsSourceData,
        filters: dict[str, Any],
        include_dashboard: bool,
        include_report: bool,
        include_powerbi: bool,
    ) -> PipelineOutput:
        """Execute the pipeline stages over a loaded source dataset."""
        cleaning = self._cleaner.clean_all(source.to_dict())
        transformed = self.transform(cleaning)
        aggregates = self.aggregate(transformed)

        output = PipelineOutput(
            status="completed",
            filters=filters,
            source=source,
            cleaning=cleaning,
            transformed=transformed,
            aggregates=aggregates,
            generated_at=now_utc().isoformat(),
        )

        if include_dashboard:
            output.dashboard_dataset = self._dashboard_builder.build(
                videos=transformed.videos,
                detections=transformed.detections,
                events=transformed.events,
                alerts=transformed.alerts,
                kpis=transformed.kpis,
            )

        if include_report:
            output.report_data = self._report_generator.generate(
                videos=transformed.videos,
                detections=transformed.detections,
                events=transformed.events,
                alerts=transformed.alerts,
                kpis=transformed.kpis,
            )

        if include_powerbi:
            output.powerbi_dataset = self._powerbi_builder.build(
                videos=transformed.videos,
                detections=transformed.detections,
                events=transformed.events,
                alerts=transformed.alerts,
                kpis=transformed.kpis,
                analytics=transformed.analytics,
            )

        total_loaded = source.total_records
        total_rejected = sum(
            result.rejected for result in cleaning.values()
        )
        logger.info(
            "Analytics pipeline completed: %d records loaded, "
            "%d rejected.",
            total_loaded,
            total_rejected,
        )
        return output


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["AnalyticsPipeline", "PipelineOutput"]

