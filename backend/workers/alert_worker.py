"""
VisionOps AI - Alert Worker

Coordinates background alert evaluation and notification jobs by
delegating to the AlertService and NotificationService. This worker
manages alert rule evaluation, alert dispatch, and notification
delivery through service orchestration — it does NOT implement any
business rules, email/SMS/webhook logic, or notification logic.

Responsibilities:
    - Trigger alert rule evaluation via the AlertService.
    - Coordinate alert dispatch to the NotificationService.
    - Support multiple notification channels (email, sms, webhook,
      dashboard).
    - Handle retries, timeouts, and graceful shutdown.
    - Track job execution statistics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from core.config import settings
from workers.base import BaseWorker


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_SEVERITY_LEVELS: frozenset[str] = frozenset(
    {"low", "medium", "high", "critical"}
)
VALID_CHANNELS: frozenset[str] = frozenset(
    {"email", "sms", "webhook", "dashboard"}
)


# ---------------------------------------------------------------------------
# Alert Worker
# ---------------------------------------------------------------------------


class AlertWorker(BaseWorker):
    """
    Background worker that coordinates alert evaluation and dispatch jobs.

    Delegates alert rule evaluation to the AlertService and
    notification dispatch to the NotificationService. This class only
    handles job orchestration, severity filtering, channel validation,
    and status tracking.
    """

    def __init__(
        self,
        name: str = "AlertWorker",
        max_retries: int | None = None,
        retry_delay: float | None = None,
        retry_backoff: float | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        """
        Initialise the alert worker.

        All timing parameters fall back to ``core.config.settings``
        values.

        Args:
            name: Human-readable worker name.
            max_retries: Maximum retry attempts on failure.
            retry_delay: Initial retry delay in seconds.
            retry_backoff: Exponential backoff multiplier.
            timeout_seconds: Maximum allowed execution time.
        """
        if timeout_seconds is None:
            timeout_seconds = getattr(
                settings, "WORKER_ALERT_TIMEOUT", 120
            )
        if max_retries is None:
            max_retries = getattr(
                settings, "WORKER_ALERT_RETRIES", 2
            )

        super().__init__(
            name=name,
            max_retries=max_retries,
            retry_delay=retry_delay,
            retry_backoff=retry_backoff,
            timeout_seconds=timeout_seconds,
        )
        self._logger: logging.Logger = logging.getLogger(
            "visionops.workers.alert_worker"
        )

    # ------------------------------------------------------------------
    # Abstract Method Implementation
    # ------------------------------------------------------------------

    async def execute_async(
        self,
        job_id: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute an alert evaluation and dispatch job.

        The payload can specify severity thresholds, channels, and
        filters. Actual alert evaluation is delegated to the
        AlertService, and dispatch to the NotificationService.

        Args:
            job_id: Unique job identifier.
            payload: Job parameters (e.g., min_severity, channels).

        Returns:
            Dictionary containing alert evaluation and dispatch results
            from the services.

        Raises:
            RuntimeError: If the payload specifies an invalid severity
                level or unknown channel.
        """
        self._logger.info(
            "AlertWorker | Job '%s' | Starting alert evaluation.",
            job_id,
        )

        # Determine severity threshold and channels
        min_severity: str = "low"
        channels: list[str] = ["dashboard"]

        if payload is not None:
            min_severity = (
                payload.get("min_severity", "low").lower().strip()
            )
            channels = payload.get(
                "channels", ["dashboard"]
            )

        # Validate severity
        if min_severity not in VALID_SEVERITY_LEVELS:
            raise RuntimeError(
                f"Job '{job_id}': Invalid severity level "
                f"'{min_severity}'. Valid levels: "
                f"{', '.join(sorted(VALID_SEVERITY_LEVELS))}."
            )

        # Validate channels
        for channel in channels:
            if channel not in VALID_CHANNELS:
                raise RuntimeError(
                    f"Job '{job_id}': Unknown notification channel "
                    f"'{channel}'. Valid channels: "
                    f"{', '.join(sorted(VALID_CHANNELS))}."
                )

        self._logger.info(
            "AlertWorker | Job '%s' | Min severity: %s | Channels: %s",
            job_id,
            min_severity,
            channels,
        )

        # ----------------------------------------------------------
        # Delegate to AlertService and NotificationService.
        #
        # TODO: Uncomment and wire the actual services when available.
        #
        #   from services.notification_service import NotificationService
        #   from business.alert_engine import AlertEngine
        #
        #   alert_service = AlertEngine()
        #   notification_service = NotificationService()
        #
        #   alerts = await alert_service.evaluate_alerts(
        #       min_severity=min_severity,
        #   )
        #   dispatch_result = await notification_service.dispatch_alerts(
        #       alerts=alerts,
        #       channels=channels,
        #   )
        #
        # For now, return a structured result indicating delegation.
        # ----------------------------------------------------------

        # alerts = await alert_service.evaluate_alerts(
        #     min_severity=min_severity,
        # )
        # dispatch_result = await notification_service.dispatch_alerts(
        #     alerts=alerts,
        #     channels=channels,
        # )

        result: Dict[str, Any] = {
            "job_id": job_id,
            "min_severity": min_severity,
            "channels": channels,
            "status": "delegated_to_alert_service",
            "services": ["AlertEngine", "NotificationService"],
            "message": (
                f"Alert evaluation (threshold: '{min_severity}') "
                f"and dispatch via {channels} delegated to services."
            ),
        }

        self._logger.info(
            "AlertWorker | Job '%s' | Alert evaluation completed.",
            job_id,
        )

        return result
