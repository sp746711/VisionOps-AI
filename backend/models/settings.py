"""VisionOps AI — Application Settings Domain Model.

This module defines the internal, framework-free **settings snapshot**
used by the application.  It is a pure *domain model*: it describes how
settings data exists internally and is *not* a FastAPI/Pydantic schema,
*not* a configuration loader, and *not* a service.

The model deliberately stays dependency-light:

- It reuses :class:`~backend.exceptions.ValidationError` for invariant
  violations instead of defining a new error type.
- It keeps datetime fields as timezone-aware UTC
  :class:`datetime.datetime` objects internally while serialising them
  to ISO 8601 strings via :meth:`Settings.to_dict`.
- Supported-value validation (e.g. the allowed ``device`` or
  ``log_level`` values) is intentionally **not** duplicated here — that
  responsibility belongs to the API schema layer
  (:mod:`backend.schemas.settings`).  Only core domain invariants are
  enforced (see :meth:`Settings._validate`).

Contents:
    - :class:`Settings` — mutable application settings snapshot.

Usage::

    from backend.models import Settings

    snapshot = Settings(project_name="VisionOps AI", confidence_threshold=0.6)
    payload = snapshot.to_dict()
    restored = Settings.from_dict(payload)
    snapshot.update(log_level="DEBUG", polling_interval=600)
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime, timezone
from typing import Any

from backend.exceptions import ValidationError

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Settings:
    """Application settings snapshot (mutable domain object).

    Represents the internally-held application configuration values used
    across the backend.  Instances are intentionally **mutable** —
    settings are updated at runtime by the settings service, so
    ``frozen=True`` is deliberately *not* applied.

    The dataclass provides structural equality and a readable ``repr``;
    instances are unhashable because they are mutable.

    Attributes:
        project_name: Human-readable application project name.
        version: Application version (semver, e.g. ``"1.0.0"``).
        environment: Deployment environment name (``development``,
            ``staging``, ``production``, ``testing``).
        debug: Whether debug mode is enabled.
        api_prefix: URL prefix used by the REST API.
        analytics_enabled: Whether the analytics pipeline is enabled.
        dashboard_enabled: Whether the dashboard endpoints are enabled.
        powerbi_enabled: Whether Power BI integration is enabled.
        bytetrack_enabled: Whether ByteTrack object tracking is enabled.
        confidence_threshold: Detection confidence threshold in
            ``[0.0, 1.0]``.
        iou_threshold: NMS IoU threshold in ``[0.0, 1.0]``.
        freshness_threshold: Freshness score threshold in ``[0, 100]``.
        max_upload_size: Maximum allowed upload size in bytes (> 0).
        polling_interval: Analytics/worker polling interval in seconds
            (> 0).
        device: Inference device name (``cpu``, ``cuda``, ``mps``,
            ``auto``).  Supported-value validation is delegated to the
            schema layer.
        log_level: Logging level (``DEBUG``, ``INFO``, ``WARNING``,
            ``ERROR``, ``CRITICAL``).  Supported-value validation is
            delegated to the schema layer.
        updated_at: Optional timezone-aware UTC timestamp of the last
            settings update.
    """

    project_name: str = "VisionOps AI"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    analytics_enabled: bool = True
    dashboard_enabled: bool = True
    powerbi_enabled: bool = False
    bytetrack_enabled: bool = True
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.45
    freshness_threshold: float = 100.0
    max_upload_size: int = 500 * 1024 * 1024  # 500 MB
    polling_interval: int = 300  # 5 minutes
    device: str = "auto"
    log_level: str = "INFO"
    updated_at: datetime | None = None

    # ------------------------------------------------------------------
    # Construction / Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Validate core domain invariants after construction.

        Raises:
            ValidationError: If any core invariant is violated.
        """
        self._validate()

    def _validate(self) -> None:
        """Enforce the core domain invariants of the settings snapshot.

        Only fundamental invariants are checked here.  Supported-value
        enumeration (device, log level, environment) is intentionally
        left to the API schema layer to avoid duplicated logic.

        Raises:
            ValidationError: If any invariant is violated.
        """
        if (
            not isinstance(self.project_name, str)
            or not self.project_name.strip()
        ):
            raise ValidationError(
                "Settings.project_name must be a non-empty string."
            )

        if not isinstance(self.version, str) or not self.version.strip():
            raise ValidationError(
                "Settings.version must be a non-empty string."
            )

        if not isinstance(self.environment, str) or not self.environment.strip():
            raise ValidationError(
                "Settings.environment must be a non-empty string."
            )

        if not isinstance(self.api_prefix, str) or not self.api_prefix.strip():
            raise ValidationError(
                "Settings.api_prefix must be a non-empty string."
            )

        if (
            not isinstance(self.confidence_threshold, (int, float))
            or not (0.0 <= float(self.confidence_threshold) <= 1.0)
        ):
            raise ValidationError(
                "Settings.confidence_threshold must be within [0.0, 1.0], "
                f"got {self.confidence_threshold!r}."
            )

        if (
            not isinstance(self.iou_threshold, (int, float))
            or not (0.0 <= float(self.iou_threshold) <= 1.0)
        ):
            raise ValidationError(
                "Settings.iou_threshold must be within [0.0, 1.0], "
                f"got {self.iou_threshold!r}."
            )

        if (
            not isinstance(self.freshness_threshold, (int, float))
            or not (0.0 <= float(self.freshness_threshold) <= 100.0)
        ):
            raise ValidationError(
                "Settings.freshness_threshold must be within [0, 100], "
                f"got {self.freshness_threshold!r}."
            )

        if not isinstance(self.max_upload_size, int) or self.max_upload_size <= 0:
            raise ValidationError(
                "Settings.max_upload_size must be a positive integer, "
                f"got {self.max_upload_size!r}."
            )

        if not isinstance(self.polling_interval, int) or self.polling_interval <= 0:
            raise ValidationError(
                "Settings.polling_interval must be a positive integer, "
                f"got {self.polling_interval!r}."
            )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the settings snapshot to a plain dictionary.

        Datetime fields are serialised to ISO 8601 strings so the output
        is JSON/CSV friendly.

        Returns:
            Dictionary mapping every field name to its value.
        """
        data: dict[str, Any] = {}
        for field_info in fields(self):
            value = getattr(self, field_info.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            data[field_info.name] = value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Settings":
        """Build a :class:`Settings` instance from a plain dictionary.

        Unknown keys are ignored, keeping the helper tolerant of
        storage-layer records that may carry extra fields.  Datetime
        values are parsed from ISO 8601 strings and normalised to
        timezone-aware UTC.

        Args:
            data: Dictionary of settings values.

        Returns:
            A new :class:`Settings` instance.

        Raises:
            ValidationError: If a provided value violates a core
                invariant or the timestamp is malformed.
        """
        known = {field_info.name for field_info in fields(cls)}
        kwargs: dict[str, Any] = {}
        for key, value in data.items():
            if key not in known:
                continue
            kwargs[key] = value

        if "updated_at" in kwargs:
            kwargs["updated_at"] = cls._coerce_datetime(kwargs["updated_at"])

        return cls(**kwargs)

    # ------------------------------------------------------------------
    # Copy / Update
    # ------------------------------------------------------------------

    def copy(self) -> "Settings":
        """Return a shallow copy of this settings snapshot.

        The copy is re-validated on construction via
        :meth:`__post_init__`.

        Returns:
            A new :class:`Settings` instance with the same field values.
        """
        return replace(self)

    def update(self, **kwargs: Any) -> "Settings":
        """Apply field updates to this snapshot in place.

        Only declared fields may be updated; unknown field names raise
        :class:`~backend.exceptions.ValidationError`.  Datetime values
        are normalised to timezone-aware UTC.  Core domain invariants
        are re-validated after the updates are applied.

        Args:
            **kwargs: Field name/value pairs to apply.

        Returns:
            ``self`` to allow method chaining.

        Raises:
            ValidationError: If an unknown field is supplied or a core
                invariant is violated after the update.
        """
        known = {field_info.name for field_info in fields(self)}
        unknown = sorted(set(kwargs) - known)
        if unknown:
            raise ValidationError(
                f"Unknown settings field(s): {', '.join(unknown)}."
            )

        for key, value in kwargs.items():
            if key == "updated_at":
                value = self._coerce_datetime(value)
            setattr(self, key, value)

        self._validate()
        return self

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_datetime(value: datetime | str | None) -> datetime | None:
        """Normalise a datetime-like value to timezone-aware UTC.

        Args:
            value: Raw timestamp (``datetime``, ISO-8601 string, or
                ``None``).

        Returns:
            Timezone-aware UTC datetime, or ``None``.

        Raises:
            ValidationError: If *value* is not a datetime, string, or
                ``None``, or if the string is not a valid ISO-8601
                timestamp.
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValidationError(
                    f"Invalid ISO-8601 timestamp: {value!r}."
                ) from exc
        else:
            raise ValidationError(
                "updated_at must be a datetime, ISO-8601 string, or None, "
                f"got {type(value).__name__}."
            )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["Settings"]

