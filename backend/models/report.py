"""VisionOps AI — Report Domain Model.

This module defines the internal, framework-free **report** domain model.
It represents a generated report record — its format, output file, scope,
and status — as produced by the report service.  It is *not* a FastAPI/
Pydantic request-response schema and *not* a service.

The model deliberately stays dependency-light:

- It reuses the :class:`~backend.schemas.common.ReportFormat` enum
  instead of redefining report formats.
- It reuses :class:`~backend.exceptions.ValidationError` for invariant
  violations.
- Report generation, export, and formatting logic belongs to the report
  service/analytics layer; only core domain invariants are enforced here
  (see :meth:`Report._validate`).

Reports are **mutable** records: their status transitions (``pending`` →
``generated`` / ``failed``) and file metadata accumulates after
generation.  Instances are therefore intentionally not frozen and not
hashable.

Contents:
    - :class:`Report` — mutable report record.

Usage::

    from backend.models import Report

    report = Report(
        report_id="rpt_001",
        format="pdf",
        title="Warehouse Report — January 2025",
        file_path="reports/pdf/rpt_001.pdf",
        status="generated",
    )
    payload = report.to_dict()
    restored = Report.from_dict(payload)
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime, timezone
from typing import Any

from backend.exceptions import ValidationError
from backend.utils.date_utils import now_utc
from backend.schemas.common import ReportFormat

#: Allowed report lifecycle statuses.
_VALID_STATUSES: frozenset[str] = frozenset(
    {"pending", "generated", "failed"}
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Report:
    """A report record (mutable domain object).

    Represents one report record in the system.  Instances are
    intentionally **mutable** so the report service can transition the
    status (``pending`` → ``generated`` / ``failed``) and attach file
    metadata after generation.  The dataclass provides structural
    equality and a readable ``repr``; instances are unhashable because
    they are mutable.

    Attributes:
        report_id: Unique report identifier (prefix ``rpt_`` in the
            service layer).
        format: Report format
            (:class:`~backend.schemas.common.ReportFormat`).
        status: Report lifecycle status — one of ``pending``,
            ``generated``, ``failed``.
        file_path: Path to the generated report file (empty while
            pending).
        file_size: Optional file size in bytes (>= 0).
        title: Optional report title.
        message: Optional status message.
        video_id: Optional video the report is scoped to.
        date_from: Optional start date of the report scope
            (``YYYY-MM-DD``).
        date_to: Optional end date of the report scope
            (``YYYY-MM-DD``).
        created_at: Timezone-aware UTC creation timestamp.
        generated_at: Optional timezone-aware UTC generation timestamp.
    """

    report_id: str
    format: ReportFormat
    status: str = "pending"
    file_path: str = ""
    file_size: int | None = None
    title: str | None = None
    message: str | None = None
    video_id: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    created_at: datetime | None = None
    generated_at: datetime | None = None

    # ------------------------------------------------------------------
    # Construction / Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Normalise status/format/timestamps and validate core invariants.

        The ``format`` value is coerced into a
        :class:`~backend.schemas.common.ReportFormat` member and
        ``status`` is normalised to lowercase (matching the schema
        layer, which accepts raw format/status strings).  All timestamps
        are normalised to timezone-aware UTC (naive values are assumed to
        be UTC).  Missing ``created_at`` is set to the current UTC time.

        Raises:
            ValidationError: If any core invariant is violated.
        """
        self.format = self._coerce_format(self.format)
        self.status = self._coerce_status(self.status)
        self.created_at = self._coerce_datetime(self.created_at)
        self.generated_at = self._coerce_datetime(self.generated_at)
        if self.created_at is None:
            self.created_at = now_utc()
        self._validate()

    def _validate(self) -> None:
        """Enforce the core domain invariants of a report record.

        Only fundamental invariants are checked here.  Report generation
        and export logic belongs to the report service/analytics layer.

        Raises:
            ValidationError: If any invariant is violated.
        """
        if not isinstance(self.report_id, str) or not self.report_id.strip():
            raise ValidationError(
                "Report.report_id must be a non-empty string."
            )

        if not isinstance(self.format, ReportFormat):
            raise ValidationError(
                "Report.format must be a ReportFormat member, got "
                f"{self.format!r}."
            )

        if not isinstance(self.status, str) or not self.status.strip():
            raise ValidationError("Report.status must be a non-empty string.")

        if self.status not in _VALID_STATUSES:
            raise ValidationError(
                f"Invalid report status {self.status!r}. "
                f"Valid: {', '.join(sorted(_VALID_STATUSES))}."
            )

        if not isinstance(self.file_path, str):
            raise ValidationError(
                "Report.file_path must be a string, got "
                f"{type(self.file_path).__name__}."
            )

        if self.file_size is not None and (
            not isinstance(self.file_size, int) or self.file_size < 0
        ):
            raise ValidationError(
                "Report.file_size must be a non-negative integer or "
                f"None, got {self.file_size!r}."
            )

        if self.title is not None and not isinstance(self.title, str):
            raise ValidationError(
                "Report.title must be a string or None, got "
                f"{type(self.title).__name__}."
            )

        if self.message is not None and not isinstance(self.message, str):
            raise ValidationError(
                "Report.message must be a string or None, got "
                f"{type(self.message).__name__}."
            )

        if self.video_id is not None and not isinstance(self.video_id, str):
            raise ValidationError(
                "Report.video_id must be a string or None, got "
                f"{type(self.video_id).__name__}."
            )

        if self.date_from is not None and not self._is_date(self.date_from):
            raise ValidationError(
                f"Report.date_from must match YYYY-MM-DD, got "
                f"{self.date_from!r}."
            )

        if self.date_to is not None and not self._is_date(self.date_to):
            raise ValidationError(
                f"Report.date_to must match YYYY-MM-DD, got "
                f"{self.date_to!r}."
            )

        if self.date_from is not None and self.date_to is not None:
            if self.date_from > self.date_to:
                raise ValidationError(
                    "Report.date_from must not be after date_to."
                )

        if self.created_at is None:
            raise ValidationError("Report.created_at must not be None.")

        if (
            self.generated_at is not None
            and self.generated_at < self.created_at
        ):
            raise ValidationError(
                "Report.generated_at must not be earlier than created_at."
            )

    # ------------------------------------------------------------------
    # Lifecycle Helpers
    # ------------------------------------------------------------------

    def mark_generated(
        self,
        file_path: str,
        file_size: int | None = None,
    ) -> "Report":
        """Mark this report as successfully generated.

        Sets the status to ``"generated"``, assigns the output file
        path/size, and stamps ``generated_at`` with the current UTC
        time.

        Args:
            file_path: Path to the generated report file.
            file_size: Optional file size in bytes (>= 0).

        Returns:
            ``self`` to allow method chaining.

        Raises:
            ValidationError: If *file_path* is empty or *file_size* is
                invalid.
        """
        if not isinstance(file_path, str) or not file_path.strip():
            raise ValidationError(
                "Report.file_path must be a non-empty string."
            )
        self.status = "generated"
        self.file_path = file_path.strip()
        self.file_size = file_size
        self.generated_at = now_utc()
        self._validate()
        return self

    def mark_failed(self, message: str | None = None) -> "Report":
        """Mark this report as failed.

        Sets the status to ``"failed"`` and optionally records an error
        message.

        Args:
            message: Optional failure description.

        Returns:
            ``self`` to allow method chaining.

        Raises:
            ValidationError: If *message* is not a string/``None``.
        """
        if message is not None and not isinstance(message, str):
            raise ValidationError(
                "Report.message must be a string or None, got "
                f"{type(message).__name__}."
            )
        self.status = "failed"
        self.message = message
        self._validate()
        return self

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report record to a plain dictionary.

        The ``format`` enum is serialised to its string value and all
        timestamps to ISO 8601 strings so the output is JSON/CSV
        friendly.

        Returns:
            Dictionary mapping every field name to its value.
        """
        data: dict[str, Any] = {}
        for field_info in fields(self):
            value = getattr(self, field_info.name)
            if isinstance(value, ReportFormat):
                value = value.value
            elif isinstance(value, datetime):
                value = value.isoformat()
            data[field_info.name] = value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Report":
        """Build a :class:`Report` instance from a plain dictionary.

        Unknown keys are ignored.  The ``format`` value is coerced into a
        :class:`~backend.schemas.common.ReportFormat` member and all
        timestamps are parsed from ISO 8601 and normalised to
        timezone-aware UTC.

        Args:
            data: Dictionary of report record values.

        Returns:
            A new :class:`Report` instance.

        Raises:
            ValidationError: If ``format``/``status`` is invalid, a
                timestamp is malformed, or a core invariant is violated.
        """
        known = {field_info.name for field_info in fields(cls)}
        kwargs: dict[str, Any] = {}
        for key, value in data.items():
            if key not in known:
                continue
            kwargs[key] = value

        if "format" in kwargs:
            kwargs["format"] = cls._coerce_format(kwargs["format"])

        if "status" in kwargs:
            kwargs["status"] = cls._coerce_status(kwargs["status"])

        for key in ("created_at", "generated_at"):
            if key in kwargs:
                kwargs[key] = cls._coerce_datetime(kwargs[key])

        return cls(**kwargs)

    # ------------------------------------------------------------------
    # Copy / Update
    # ------------------------------------------------------------------

    def copy(self) -> "Report":
        """Return a shallow copy of this report record.

        The copy is re-validated on construction via
        :meth:`__post_init__`.

        Returns:
            A new :class:`Report` instance with the same field values.
        """
        return replace(self)

    def update(self, **kwargs: Any) -> "Report":
        """Apply field updates to this report record in place.

        Only declared fields may be updated; unknown field names raise
        :class:`~backend.exceptions.ValidationError`.  The ``format``
        value is coerced into a :class:`~backend.schemas.common.ReportFormat`
        member and all timestamps are normalised to timezone-aware UTC.
        Core domain invariants are re-validated after the updates are
        applied.

        Args:
            **kwargs: Field name/value pairs to apply.

        Returns:
            ``self`` to allow method chaining.

        Raises:
            ValidationError: If an unknown field is supplied, ``format``
                or ``status`` is invalid, or a core invariant is violated
                after the update.
        """
        known = {field_info.name for field_info in fields(self)}
        unknown = sorted(set(kwargs) - known)
        if unknown:
            raise ValidationError(
                f"Unknown report field(s): {', '.join(unknown)}."
            )

        if "format" in kwargs:
            kwargs["format"] = self._coerce_format(kwargs["format"])
        if "status" in kwargs:
            kwargs["status"] = self._coerce_status(kwargs["status"])

        for key in ("created_at", "generated_at"):
            if key in kwargs:
                kwargs[key] = self._coerce_datetime(kwargs[key])

        for key, value in kwargs.items():
            setattr(self, key, value)

        self._validate()
        return self

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_format(value: str | ReportFormat) -> ReportFormat:
        """Coerce a raw format value into a :class:`ReportFormat` member.

        Args:
            value: Raw format value (enum member or string).

        Returns:
            The corresponding :class:`ReportFormat` member.

        Raises:
            ValidationError: If *value* is not a valid report format.
        """
        if isinstance(value, ReportFormat):
            return value
        try:
            return ReportFormat(value.strip().lower())
        except (AttributeError, ValueError) as exc:
            valid = ", ".join(sorted(f.value for f in ReportFormat))
            raise ValidationError(
                f"Invalid format {value!r}. Valid formats: {valid}."
            ) from exc

    @staticmethod
    def _coerce_status(value: str) -> str:
        """Normalise a raw report status string.

        Args:
            value: Raw status string.

        Returns:
            The stripped, lowercased status string.

        Raises:
            ValidationError: If *value* is empty or not a valid report
                status.
        """
        if not isinstance(value, str):
            raise ValidationError(
                "Report.status must be a string, got "
                f"{type(value).__name__}."
            )
        normalized = value.strip().lower()
        if normalized not in _VALID_STATUSES:
            raise ValidationError(
                f"Invalid report status {value!r}. "
                f"Valid: {', '.join(sorted(_VALID_STATUSES))}."
            )
        return normalized

    @staticmethod
    def _is_date(value: str) -> bool:
        """Return whether *value* matches the ``YYYY-MM-DD`` format."""
        if not isinstance(value, str):
            return False
        parts = value.strip().split("-")
        if len(parts) != 3:
            return False
        try:
            datetime(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, TypeError):
            return False
        return True

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
                "Timestamp must be a datetime, ISO-8601 string, or None, "
                f"got {type(value).__name__}."
            )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = ["Report"]

