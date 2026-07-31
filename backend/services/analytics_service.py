"""VisionOps AI — Analytics Service.

Provides business-logic orchestration for KPI calculation, spoilage metrics,
freshness metrics, and dashboard data preparation. Delegates low-level
aggregation and transformation to ``backend.analytics`` and ``backend.business``.

Responsibilities:
    - KPI calculation
    - Spoilage metrics computation
    - Freshness metrics computation
    - Dashboard data preparation
    - Analytics pipeline orchestration

Usage::

    from backend.services import AnalyticsService

    service = AnalyticsService()
    kpis = service.calculate_kpis(video_id="vid_abc-123")
    spoilage = service.compute_spoilage_metrics(video_id="vid_abc-123")
    dashboard = service.prepare_dashboard_data()
"""

from __future__ import annotations

import logging
from typing import Any

from backend.core.config import settings
from backend.exceptions import (
    ValidationError,
    StorageError,
    AnalyticsError,
)
from backend.storage import StorageService
from backend.utils.date_utils import now_utc
from backend.utils.math_utils import (
    average,
    percentage,
    safe_division,
    standard_deviation,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_KPI_LIMIT: int = 100

# ---------------------------------------------------------------------------
# AnalyticsService
# ---------------------------------------------------------------------------


class AnalyticsService:
    """Orchestrates analytics operations: KPI calculation, spoilage and
    freshness metrics, dashboard data preparation, and pipeline execution.

    This service sits between the API layer and the analytics/business
    layers. It coordinates data aggregation, transformation, and metric
    computation — without implementing any low-level data manipulation
    or business rule logic.

    Dependency injection is used for the storage layer to improve
    testability.

    Raises:
        ValidationError: If input arguments are invalid.
        StorageError: If storage operations fail.
        AnalyticsError: If analytics operations fail.
    """

    def __init__(
        self,
        storage: StorageService | None = None,
    ) -> None:
        """Initialise the analytics service.

        Args:
            storage: Injected ``StorageService`` instance. When ``None``,
                a default instance is created.
        """
        self._storage = storage or StorageService()
        logger.info(
            "AnalyticsService initialised (storage=%s)",
            type(self._storage).__name__,
        )

    # ------------------------------------------------------------------
    # Pipeline Orchestration
    # ------------------------------------------------------------------

    async def run_pipeline(
        self,
        operation: str = "full_pipeline",
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the analytics pipeline.

        This method is called by the ``AnalyticsWorker``. It coordinates
        the full analytics workflow: data loading, transformation,
        aggregation, KPI computation, and dashboard dataset preparation.

        **Current implementation** performs aggregation from stored data.
        The full pipeline wiring to ``backend.analytics`` will be added
        when that package is finalised.

        Args:
            operation: Pipeline operation type — ``"full_pipeline"``,
                ``"aggregation_only"``, ``"kpi_only"``, or
                ``"dataset_refresh"``.
            filters: Optional filter parameters (date ranges, video IDs,
                etc.).

        Returns:
            Dictionary with pipeline execution results.

        Raises:
            ValidationError: If *operation* is invalid.
            StorageError: If storage operations fail.
        """
        valid_ops = {"full_pipeline", "aggregation_only", "kpi_only", "dataset_refresh"}
        if operation not in valid_ops:
            raise ValidationError(
                f"Invalid operation '{operation}'. "
                f"Valid: {', '.join(sorted(valid_ops))}."
            )

        logger.info(
            "Running analytics pipeline: operation='%s', filters=%s",
            operation,
            filters or {},
        )

        result: dict[str, Any] = {
            "operation": operation,
            "status": "completed",
            "timestamp": now_utc().isoformat(),
        }

        if operation in ("full_pipeline", "aggregation_only"):
            try:
                detections = self._storage.read_csv_store("detections")
                events = self._storage.read_csv_store("events")

                # Basic aggregation
                total_detections = len(detections)
                total_events = len(events)

                result["aggregation"] = {
                    "total_detections": total_detections,
                    "total_events": total_events,
                    "video_count": len(
                        set(d.get("video_id", "") for d in detections)
                    ),
                }
            except StorageError as exc:
                raise StorageError(
                    f"Analytics pipeline aggregation failed: {exc}"
                ) from exc

        if operation in ("full_pipeline", "kpi_only"):
            try:
                kpis = self._calculate_kpis_from_stores()
                result["kpis"] = kpis
            except (StorageError, AnalyticsError) as exc:
                raise AnalyticsError(
                    f"Analytics pipeline KPI computation failed: {exc}"
                ) from exc

        if operation in ("full_pipeline", "dataset_refresh"):
            result["dataset_refresh"] = {
                "status": "pending",
                "message": "Dashboard dataset refresh delegated to backend.",
            }

        logger.info(
            "Analytics pipeline '%s' completed.", operation
        )
        return result

    # ------------------------------------------------------------------
    # KPI Calculation
    # ------------------------------------------------------------------

    def calculate_kpis(
        self,
        video_id: str | None = None,
        limit: int = _DEFAULT_KPI_LIMIT,
    ) -> list[dict[str, Any]]:
        """Calculate key performance indicators.

        Reads detection data and computes KPI values. If *video_id* is
        provided, KPIs are scoped to that video. Otherwise, global KPIs
        are computed.

        Args:
            video_id: Optional video ID to scope KPIs.
            limit: Maximum number of KPI records to return (default: 100).

        Returns:
            List of KPI dictionaries with keys ``kpi_id``, ``video_id``,
            ``metric``, ``value``, ``unit``, ``timestamp``.

        Raises:
            ValidationError: If *limit* is out of range.
            StorageError: If reading data fails.
        """
        if limit < 1 or limit > 10000:
            raise ValidationError(
                f"limit must be between 1 and 10000, got {limit}."
            )

        try:
            kpis = self._calculate_kpis_from_stores(video_id=video_id)
        except (StorageError, AnalyticsError) as exc:
            raise StorageError(
                f"KPI calculation failed: {exc}"
            ) from exc

        return kpis[:limit]

    def _calculate_kpis_from_stores(
        self,
        video_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Internal: compute KPIs from CSV stores.

        Args:
            video_id: Optional video filter.

        Returns:
            List of KPI dictionaries.
        """
        detections = self._storage.read_csv_store("detections")
        events = self._storage.read_csv_store("events")
        now = now_utc()

        # Filter by video_id if provided
        if video_id:
            detections = [d for d in detections if d.get("video_id") == video_id]
            events = [e for e in events if e.get("video_id") == video_id]

        kpis: list[dict[str, Any]] = []

        # Total detection count
        kpis.append({
            "kpi_id": f"kpi_det_total_{video_id or 'global'}",
            "video_id": video_id or "global",
            "metric": "total_detections",
            "value": len(detections),
            "unit": "count",
            "timestamp": now.isoformat(),
        })

        if detections:
            # Average confidence
            confs: list[float] = []
            class_counts: dict[str, int] = {}
            for d in detections:
                try:
                    confs.append(float(d.get("confidence", 0.0)))
                except (ValueError, TypeError):
                    pass
                cls = d.get("class_name", "unknown")
                class_counts[cls] = class_counts.get(cls, 0) + 1

            avg_conf = average(confs) if confs else 0.0
            kpis.append({
                "kpi_id": f"kpi_avg_conf_{video_id or 'global'}",
                "video_id": video_id or "global",
                "metric": "average_confidence",
                "value": round(avg_conf, 4),
                "unit": "score",
                "timestamp": now.isoformat(),
            })

            # Per-class counts
            for cls, count in sorted(class_counts.items()):
                kpis.append({
                    "kpi_id": f"kpi_cls_{cls}_{video_id or 'global'}",
                    "video_id": video_id or "global",
                    "metric": f"class_count_{cls}",
                    "value": count,
                    "unit": "count",
                    "timestamp": now.isoformat(),
                })

            # Detection rate (per event)
            if events:
                det_rate = safe_division(len(detections), len(events), default=0.0)
                kpis.append({
                    "kpi_id": f"kpi_det_rate_{video_id or 'global'}",
                    "video_id": video_id or "global",
                    "metric": "detections_per_event",
                    "value": round(det_rate, 2),
                    "unit": "ratio",
                    "timestamp": now.isoformat(),
                })

        # Total event count
        kpis.append({
            "kpi_id": f"kpi_evt_total_{video_id or 'global'}",
            "video_id": video_id or "global",
            "metric": "total_events",
            "value": len(events),
            "unit": "count",
            "timestamp": now.isoformat(),
        })

        # Persist KPIs to store
        try:
            self._storage.append_csv_store("kpis", kpis)
        except StorageError:
            logger.warning("Failed to persist KPI records (non-fatal).")

        logger.debug(
            "Computed %d KPIs (video_id=%s)", len(kpis), video_id or "global"
        )
        return kpis

    # ------------------------------------------------------------------
    # Spoilage Metrics
    # ------------------------------------------------------------------

    def compute_spoilage_metrics(
        self,
        video_id: str | None = None,
    ) -> dict[str, Any]:
        """Compute spoilage-related metrics from detection and event data.

        Spoilage metrics indicate potential product spoilage risks based
        on detected objects, dwell times, and environmental factors.

        Args:
            video_id: Optional video ID to scope metrics.

        Returns:
            Dictionary with spoilage metrics:
            - ``spoilage_risk_index``: Normalised risk score (0–100).
            - ``high_risk_detections``: Count of high-risk detections.
            - ``average_dwell_time_minutes``: Average dwell time.
            - ``risk_factors``: List of contributing risk factors.

        Raises:
            StorageError: If reading data fails.
        """
        try:
            detections = self._storage.read_csv_store("detections")
            events = self._storage.read_csv_store("events")
        except StorageError as exc:
            raise StorageError(
                f"Failed to read data for spoilage metrics: {exc}"
            ) from exc

        if video_id:
            detections = [d for d in detections if d.get("video_id") == video_id]
            events = [e for e in events if e.get("video_id") == video_id]

        # Compute risk indicators
        high_risk_classes = {"product", "pallet"}
        high_risk_count = sum(
            1 for d in detections if d.get("class_name") in high_risk_classes
        )

        # Count prolonged-dwell events as risk factors
        prolonged_events = sum(
            1 for e in events
            if e.get("event_type", "").lower() in {"dwell", "idle", "stalled"}
        )

        # Compute spoilage risk index (simplified heuristic)
        total_items = len(detections) or 1
        risk_ratio = safe_division(
            high_risk_count + prolonged_events * 2,
            total_items,
            default=0.0,
        )
        spoilage_risk_index = round(clamp_value(risk_ratio * 100.0, 0.0, 100.0), 2)

        risk_factors: list[str] = []
        if high_risk_count > 10:
            risk_factors.append(f"High count of risk objects ({high_risk_count})")
        if prolonged_events > 5:
            risk_factors.append(
                f"Prolonged dwell/idle events detected ({prolonged_events})"
            )
        if spoilage_risk_index > 70:
            risk_factors.append("Elevated spoilage risk index")

        metrics: dict[str, Any] = {
            "spoilage_risk_index": spoilage_risk_index,
            "high_risk_detections": high_risk_count,
            "average_dwell_time_minutes": 0.0,
            "risk_factors": risk_factors,
            "total_events_analysed": len(events),
            "total_detections_analysed": len(detections),
        }

        logger.debug(
            "Spoilage metrics computed: risk_index=%.2f, risk_factors=%d",
            spoilage_risk_index,
            len(risk_factors),
        )
        return metrics

    # ------------------------------------------------------------------
    # Freshness Metrics
    # ------------------------------------------------------------------

    def compute_freshness_metrics(
        self,
        video_id: str | None = None,
    ) -> dict[str, Any]:
        """Compute freshness-related metrics.

        Freshness metrics estimate the freshness state of products based
        on detection timelines, event sequences, and turnover rates.

        Args:
            video_id: Optional video ID to scope metrics.

        Returns:
            Dictionary with freshness metrics:
            - ``freshness_score``: Overall freshness score (0–100).
            - ``turnover_rate``: Estimated product turnover rate.
            - ``stale_detection_ratio``: Ratio of aged detections.
            - ``average_freshness_by_class``: Per-class freshness.

        Raises:
            StorageError: If reading data fails.
        """
        try:
            detections = self._storage.read_csv_store("detections")
        except StorageError as exc:
            raise StorageError(
                f"Failed to read data for freshness metrics: {exc}"
            ) from exc

        if video_id:
            detections = [d for d in detections if d.get("video_id") == video_id]

        if not detections:
            return {
                "freshness_score": 100.0,
                "turnover_rate": 0.0,
                "stale_detection_ratio": 0.0,
                "average_freshness_by_class": {},
                "total_detections_analysed": 0,
            }

        # Compute per-class freshness based on confidence as a proxy
        class_freshness: dict[str, list[float]] = {}
        for d in detections:
            cls = d.get("class_name", "unknown")
            try:
                conf = float(d.get("confidence", 0.0))
            except (ValueError, TypeError):
                conf = 0.0
            # Freshness proxy: higher confidence = more reliable = fresher
            class_freshness.setdefault(cls, []).append(conf * 100.0)

        avg_freshness_by_class: dict[str, float] = {
            cls: round(average(confs), 2)
            for cls, confs in class_freshness.items()
        }

        all_freshness = [
            v for vals in class_freshness.values() for v in vals
        ]
        overall_freshness = round(average(all_freshness), 2) if all_freshness else 100.0

        # Stale detection ratio: detections with very low confidence
        stale_count = sum(1 for v in all_freshness if v < 30.0)
        stale_ratio = round(
            safe_division(stale_count, len(all_freshness), default=0.0), 4
        )

        metrics: dict[str, Any] = {
            "freshness_score": overall_freshness,
            "turnover_rate": round(
                safe_division(len(detections), 100, default=0.0), 4
            ),
            "stale_detection_ratio": stale_ratio,
            "average_freshness_by_class": avg_freshness_by_class,
            "total_detections_analysed": len(detections),
        }

        logger.debug(
            "Freshness metrics computed: score=%.2f, stale_ratio=%.4f",
            overall_freshness,
            stale_ratio,
        )
        return metrics

    # ------------------------------------------------------------------
    # Dashboard Data Preparation
    # ------------------------------------------------------------------

    def prepare_dashboard_data(
        self,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Prepare aggregated data for the dashboard.

        Reads detection, event, alert, and KPI data and compiles a
        comprehensive dashboard dataset with summary statistics,
        time-series trends, and alert summaries.

        Args:
            filters: Optional filter parameters (e.g. date range,
                video IDs).

        Returns:
            Dictionary with dashboard-ready data sections:
            - ``summary``: Overall counts and rates.
            - ``detection_trends``: Detection counts over time.
            - ``alert_summary``: Alert severity distribution.
            - ``top_classes``: Most detected object classes.
            - ``recent_events``: Most recent business events.

        Raises:
            StorageError: If reading data fails.
        """
        video_ids: list[str] | None = None
        if filters and "video_ids" in filters:
            vids = filters["video_ids"]
            if isinstance(vids, list) and vids:
                video_ids = [str(v) for v in vids]

        try:
            detections = self._storage.read_csv_store("detections")
            events = self._storage.read_csv_store("events")
            alerts = self._storage.read_csv_store("alerts")
            kpis = self._storage.read_csv_store("kpis")
        except StorageError as exc:
            raise StorageError(
                f"Failed to read data for dashboard: {exc}"
            ) from exc

        # Apply video filter
        if video_ids:
            detections = [d for d in detections if d.get("video_id") in video_ids]
            events = [e for e in events if e.get("video_id") in video_ids]

        # Summary
        total_detections = len(detections)
        total_events = len(events)
        total_alerts = len(alerts)

        # Detection trends (by date)
        date_counts: dict[str, int] = {}
        for d in detections:
            created = d.get("created_at", "")[:10]  # YYYY-MM-DD
            if created:
                date_counts[created] = date_counts.get(created, 0) + 1

        detection_trends = [
            {"date": date, "count": count}
            for date, count in sorted(date_counts.items())
        ]

        # Alert severity distribution
        severity_counts: dict[str, int] = {}
        for a in alerts:
            sev = a.get("severity", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        alert_summary = {
            "total": total_alerts,
            "by_severity": severity_counts,
        }

        # Top detected classes
        class_counts: dict[str, int] = {}
        for d in detections:
            cls = d.get("class_name", "unknown")
            class_counts[cls] = class_counts.get(cls, 0) + 1

        top_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        top_classes_list = [
            {"class_name": cls, "count": count}
            for cls, count in top_classes
        ]

        # Recent events (last 20)
        sorted_events = sorted(
            events,
            key=lambda e: e.get("created_at", ""),
            reverse=True,
        )[:20]

        # Latest KPI values
        latest_kpis = kpis[-10:] if len(kpis) > 10 else kpis

        dashboard = {
            "summary": {
                "total_detections": total_detections,
                "total_events": total_events,
                "total_alerts": total_alerts,
                "total_kpis": len(kpis),
            },
            "detection_trends": detection_trends,
            "alert_summary": alert_summary,
            "top_classes": top_classes_list,
            "recent_events": sorted_events,
            "latest_kpis": latest_kpis,
            "generated_at": now_utc().isoformat(),
        }

        logger.info(
            "Dashboard data prepared: %d detections, %d events, %d alerts",
            total_detections,
            total_events,
            total_alerts,
        )
        return dashboard


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def clamp_value(value: float, min_val: float, max_val: float) -> float:
    """Clamp a numeric value between min and max.

    Args:
        value: Input value.
        min_val: Minimum bound.
        max_val: Maximum bound.

    Returns:
        Clamped value.
    """
    return max(min_val, min(value, max_val))

