"""VisionOps AI — Notification Service.

Provides business-logic orchestration for alert dispatch, notification
delivery, and channel management. Delegates low-level communication
(whether email, SMS, webhook, or dashboard) to dedicated delivery
providers — this service only coordinates the dispatch workflow.

Responsibilities:
    - Alert dispatch to multiple channels
    - Email notification preparation
    - Webhook notification preparation
    - Dashboard notification preparation
    - Notification acknowledgement tracking

Usage::

    from backend.services import NotificationService

    service = NotificationService()
    result = service.dispatch_alerts(alerts=[...], channels=["email", "dashboard"])
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.core.config import settings
from backend.exceptions import (
    ValidationError,
    StorageError,
    RequiredFieldError,
)
from backend.storage import StorageService
from backend.utils.date_utils import now_utc
from backend.utils.id_generator import generate_uuid4

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_CHANNELS: frozenset[str] = frozenset(
    {"email", "sms", "webhook", "dashboard"}
)
_NOTIFICATION_ID_PREFIX: str = "notif_"
_DEFAULT_CHANNELS: list[str] = ["dashboard"]

# ---------------------------------------------------------------------------
# NotificationService
# ---------------------------------------------------------------------------


class NotificationService:
    """Orchestrates alert dispatch to multiple notification channels.

    This service sits between the business layer (alert evaluation) and
    the delivery layer (email, webhook, dashboard). It coordinates
    the dispatch workflow, validates channels, and tracks delivery
    status — without implementing any low-level communication logic.

    Dependency injection is used for the storage layer to improve
    testability.

    Raises:
        ValidationError: If input arguments are invalid.
        StorageError: If storage operations fail.
    """

    def __init__(
        self,
        storage: StorageService | None = None,
    ) -> None:
        """Initialise the notification service.

        Args:
            storage: Injected ``StorageService`` instance. When ``None``,
                a default instance is created.
        """
        self._storage = storage or StorageService()
        logger.info(
            "NotificationService initialised (storage=%s)",
            type(self._storage).__name__,
        )

    # ------------------------------------------------------------------
    # Alert Dispatch
    # ------------------------------------------------------------------

    def dispatch_alerts(
        self,
        alerts: list[dict[str, Any]],
        channels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Dispatch a list of alerts to the specified channels.

        This method is called by the ``AlertWorker``. It validates
        the alerts and channels, dispatches each alert to every
        requested channel, and tracks delivery status.

        Args:
            alerts: List of alert dictionaries to dispatch. Each alert
                should contain at minimum ``alert_id``, ``severity``,
                ``message``, and ``created_at``.
            channels: List of target channels. If ``None``, defaults to
                ``["dashboard"]``.

        Returns:
            Dictionary with dispatch results:
            - ``total_alerts``: Number of alerts processed.
            - ``channels_used``: Channels dispatched to.
            - ``successful_dispatches``: Count of successful dispatches.
            - ``failed_dispatches``: Count of failed dispatches.
            - ``dispatch_results``: Per-alert, per-channel results.
            - ``timestamp``: ISO-8601 timestamp.

        Raises:
            ValidationError: If any alert or channel is invalid.
        """
        channels = channels or list(_DEFAULT_CHANNELS)

        # Validate channels
        for channel in channels:
            if channel not in _VALID_CHANNELS:
                raise ValidationError(
                    f"Invalid notification channel '{channel}'. "
                    f"Valid channels: {', '.join(sorted(_VALID_CHANNELS))}."
                )

        if not alerts:
            logger.info("No alerts to dispatch.")
            return {
                "total_alerts": 0,
                "channels_used": channels,
                "successful_dispatches": 0,
                "failed_dispatches": 0,
                "dispatch_results": [],
                "timestamp": now_utc().isoformat(),
            }

        logger.info(
            "Dispatching %d alerts to channels: %s",
            len(alerts),
            channels,
        )

        dispatch_results: list[dict[str, Any]] = []
        successful = 0
        failed = 0

        for alert in alerts:
            alert_id = alert.get("alert_id", "unknown")
            for channel in channels:
                try:
                    result = self._dispatch_to_channel(alert, channel)
                    dispatch_results.append(result)
                    if result.get("status") == "sent":
                        successful += 1
                    else:
                        failed += 1
                except Exception as exc:
                    failed += 1
                    dispatch_results.append({
                        "alert_id": alert_id,
                        "channel": channel,
                        "status": "failed",
                        "error": str(exc),
                    })
                    logger.error(
                        "Failed to dispatch alert '%s' to '%s': %s",
                        alert_id,
                        channel,
                        exc,
                    )

        results: dict[str, Any] = {
            "total_alerts": len(alerts),
            "channels_used": channels,
            "successful_dispatches": successful,
            "failed_dispatches": failed,
            "dispatch_results": dispatch_results,
            "timestamp": now_utc().isoformat(),
        }

        logger.info(
            "Alert dispatch completed: %d sent, %d failed",
            successful,
            failed,
        )
        return results

    # ------------------------------------------------------------------
    # Email Notification
    # ------------------------------------------------------------------

    def send_email_notification(
        self,
        recipient: str,
        subject: str,
        body: str,
        alert_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Prepare and send an email notification.

        **Current implementation** validates and queues the email
        request. Actual email sending will be wired to an email provider
        when available.

        Args:
            recipient: Email address of the recipient.
            subject: Email subject line.
            body: Email body content (plain text or HTML).
            alert_data: Optional alert data to include.

        Returns:
            Dictionary with email notification status.

        Raises:
            RequiredFieldError: If *recipient*, *subject*, or *body*
                are empty.
        """
        if not recipient:
            raise RequiredFieldError(
                "recipient is required for email notification.",
                field="recipient",
            )
        if not subject:
            raise RequiredFieldError(
                "subject is required for email notification.",
                field="subject",
            )
        if not body:
            raise RequiredFieldError(
                "body is required for email notification.",
                field="body",
            )

        notification_id = f"{_NOTIFICATION_ID_PREFIX}{generate_uuid4()}"

        # TODO: Wire actual email sending when email provider is available.
        #   from backend.utils.email import send_email
        #   send_email(to=recipient, subject=subject, body=body)

        logger.info(
            "Email notification prepared: to='%s', subject='%s'",
            recipient,
            subject,
        )

        result: dict[str, Any] = {
            "notification_id": notification_id,
            "channel": "email",
            "recipient": recipient,
            "subject": subject,
            "status": "queued",
            "message": "Email notification queued for delivery.",
            "timestamp": now_utc().isoformat(),
        }

        # Persist to alerts store as a notification record
        self._persist_notification(result, alert_data)

        return result

    # ------------------------------------------------------------------
    # Webhook Notification
    # ------------------------------------------------------------------

    def send_webhook_notification(
        self,
        url: str,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Prepare and send a webhook notification.

        **Current implementation** validates and queues the webhook
        request. Actual HTTP delivery will be wired when available.

        Args:
            url: Target webhook URL.
            payload: JSON-serializable payload to send.
            headers: Optional HTTP headers to include.

        Returns:
            Dictionary with webhook notification status.

        Raises:
            RequiredFieldError: If *url* or *payload* are empty.
            ValidationError: If *url* is not a valid HTTP(S) URL.
        """
        if not url:
            raise RequiredFieldError(
                "url is required for webhook notification.",
                field="url",
            )
        if not payload:
            raise RequiredFieldError(
                "payload is required for webhook notification.",
                field="payload",
            )

        if not url.startswith(("http://", "https://")):
            raise ValidationError(
                f"Webhook URL must start with http:// or https://, got '{url}'."
            )

        notification_id = f"{_NOTIFICATION_ID_PREFIX}{generate_uuid4()}"

        # TODO: Wire actual webhook delivery when available.
        #   import httpx
        #   async with httpx.AsyncClient() as client:
        #       response = await client.post(url, json=payload, headers=headers)

        logger.info(
            "Webhook notification prepared: url='%s', payload_size=%d",
            url,
            len(json.dumps(payload)),
        )

        result: dict[str, Any] = {
            "notification_id": notification_id,
            "channel": "webhook",
            "url": url,
            "status": "queued",
            "message": "Webhook notification queued for delivery.",
            "timestamp": now_utc().isoformat(),
        }

        self._persist_notification(result, payload)

        return result

    # ------------------------------------------------------------------
    # Dashboard Notification
    # ------------------------------------------------------------------

    def send_dashboard_notification(
        self,
        message: str,
        alert_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create an in-dashboard notification.

        Dashboard notifications are persisted to the alerts store and
        can be retrieved by the dashboard API.

        Args:
            message: Notification message text.
            alert_data: Optional alert data to include.

        Returns:
            Dictionary with dashboard notification status.

        Raises:
            RequiredFieldError: If *message* is empty.
        """
        if not message:
            raise RequiredFieldError(
                "message is required for dashboard notification.",
                field="message",
            )

        notification_id = f"{_NOTIFICATION_ID_PREFIX}{generate_uuid4()}"

        result: dict[str, Any] = {
            "notification_id": notification_id,
            "channel": "dashboard",
            "message": message,
            "status": "displayed",
            "acknowledged": "false",
            "timestamp": now_utc().isoformat(),
        }

        self._persist_notification(result, alert_data)

        logger.info(
            "Dashboard notification created: id='%s'",
            notification_id,
        )
        return result

    # ------------------------------------------------------------------
    # Acknowledgement
    # ------------------------------------------------------------------

    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str | None = None,
    ) -> dict[str, Any]:
        """Mark an alert as acknowledged.

        Args:
            alert_id: Unique alert identifier.
            acknowledged_by: Optional identifier of who acknowledged
                the alert.

        Returns:
            Updated alert record.

        Raises:
            RequiredFieldError: If *alert_id* is empty.
            StorageError: If the alert is not found or update fails.
        """
        if not alert_id:
            raise RequiredFieldError(
                "alert_id is required.", field="alert_id"
            )

        now = now_utc()
        update_data: dict[str, Any] = {
            "acknowledged": "true",
            "acknowledged_at": now.isoformat(),
        }
        if acknowledged_by:
            update_data["acknowledged_by"] = acknowledged_by

        found: dict[str, Any] | None = None

        def match_fn(row: dict[str, Any]) -> bool:
            return row.get("alert_id") == alert_id

        def update_fn(row: dict[str, Any]) -> dict[str, Any]:
            nonlocal found
            row.update(update_data)
            found = dict(row)
            return row

        try:
            updated_count = self._storage.csv_manager.update_rows(
                "alerts", match_fn, update_fn
            )
        except StorageError as exc:
            raise StorageError(
                f"Failed to acknowledge alert '{alert_id}': {exc}"
            ) from exc

        if updated_count == 0:
            raise StorageError(
                f"Alert not found: '{alert_id}'."
            )

        logger.info(
            "Alert '%s' acknowledged by '%s'.",
            alert_id,
            acknowledged_by or "unknown",
        )
        return found or {}

    # ------------------------------------------------------------------
    # Escalation Logic
    # ------------------------------------------------------------------

    def escalate_alert(
        self,
        alert_id: str,
        escalation_level: int = 1,
    ) -> dict[str, Any]:
        """Escalate an unacknowledged alert to a higher severity level.

        Args:
            alert_id: Unique alert identifier.
            escalation_level: Escalation step (1 = first escalation,
                2 = second, etc.).

        Returns:
            Updated alert record with escalated severity.

        Raises:
            ValidationError: If *escalation_level* is invalid.
            StorageError: If the alert is not found or update fails.
        """
        if escalation_level < 1 or escalation_level > 5:
            raise ValidationError(
                f"escalation_level must be between 1 and 5, got {escalation_level}."
            )

        # Fetch current alert
        try:
            alerts = self._storage.read_csv_store("alerts")
        except StorageError as exc:
            raise StorageError(
                f"Failed to read alerts for escalation: {exc}"
            ) from exc

        target: dict[str, Any] | None = None
        for alert in alerts:
            if alert.get("alert_id") == alert_id:
                target = alert
                break

        if target is None:
            raise StorageError(f"Alert not found: '{alert_id}'.")

        # Determine escalated severity
        severity_order = ["low", "medium", "high", "critical"]
        current_severity = target.get("severity", "low").lower().strip()
        try:
            current_idx = severity_order.index(current_severity)
        except ValueError:
            current_idx = 0

        new_idx = min(current_idx + escalation_level, len(severity_order) - 1)
        new_severity = severity_order[new_idx]

        # Update the alert
        now = now_utc()
        update_data: dict[str, Any] = {
            "severity": new_severity,
            "escalated": "true",
            "escalation_level": str(escalation_level),
            "updated_at": now.isoformat(),
        }

        found: dict[str, Any] | None = None

        def match_fn(row: dict[str, Any]) -> bool:
            return row.get("alert_id") == alert_id

        def update_fn(row: dict[str, Any]) -> dict[str, Any]:
            nonlocal found
            row.update(update_data)
            found = dict(row)
            return row

        try:
            self._storage.csv_manager.update_rows("alerts", match_fn, update_fn)
        except StorageError as exc:
            raise StorageError(
                f"Failed to escalate alert '{alert_id}': {exc}"
            ) from exc

        logger.info(
            "Alert '%s' escalated to '%s' (level %d).",
            alert_id,
            new_severity,
            escalation_level,
        )
        return found or {}

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _dispatch_to_channel(
        self,
        alert: dict[str, Any],
        channel: str,
    ) -> dict[str, Any]:
        """Dispatch a single alert to a single channel.

        Args:
            alert: Alert dictionary.
            channel: Target channel name.

        Returns:
            Dispatch result dictionary.
        """
        alert_id = alert.get("alert_id", "unknown")
        message = alert.get("message", "No message")
        severity = alert.get("severity", "low")

        if channel == "email":
            recipient = settings.ALERT_EMAIL_RECIPIENT if hasattr(
                settings, "ALERT_EMAIL_RECIPIENT"
            ) else "alerts@visionops.ai"
            return self.send_email_notification(
                recipient=recipient,
                subject=f"[VisionOps AI] Alert: {severity.upper()} - {alert_id}",
                body=f"Severity: {severity}\n\n{message}",
                alert_data=alert,
            )

        if channel == "webhook":
            webhook_url = settings.ALERT_WEBHOOK_URL if hasattr(
                settings, "ALERT_WEBHOOK_URL"
            ) else "http://localhost:8000/webhook/alerts"
            return self.send_webhook_notification(
                url=webhook_url,
                payload={
                    "alert_id": alert_id,
                    "severity": severity,
                    "message": message,
                    "timestamp": now_utc().isoformat(),
                },
            )

        if channel == "dashboard":
            return self.send_dashboard_notification(
                message=f"[{severity.upper()}] {message}",
                alert_data=alert,
            )

        # SMS (placeholder)
        if channel == "sms":
            notification_id = f"{_NOTIFICATION_ID_PREFIX}{generate_uuid4()}"
            result: dict[str, Any] = {
                "notification_id": notification_id,
                "channel": "sms",
                "alert_id": alert_id,
                "status": "queued",
                "message": "SMS notification queued (not yet implemented).",
                "timestamp": now_utc().isoformat(),
            }
            self._persist_notification(result, alert)
            return result

        raise ValidationError(f"Unsupported channel: '{channel}'.")

    def _persist_notification(
        self,
        notification: dict[str, Any],
        related_data: dict[str, Any] | None = None,
    ) -> None:
        """Persist a notification record to the alerts store.

        Args:
            notification: Notification dictionary to persist.
            related_data: Optional related data to merge.
        """
        record = dict(notification)
        if related_data:
            # Merge non-overlapping fields from related data
            for key, value in related_data.items():
                if key not in record:
                    record[key] = value

        try:
            self._storage.append_csv_store("alerts", [record])
        except StorageError:
            logger.warning(
                "Failed to persist notification record (non-fatal)."
            )

