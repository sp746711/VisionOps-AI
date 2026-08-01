"""VisionOps AI — User Domain Model.

This module defines the internal, framework-free **user** domain model.
It represents how user records exist internally (as handled by the
auth service and persisted via the storage layer) and is *not* a
FastAPI/Pydantic request-response schema and *not* a service.

The model deliberately stays dependency-light:

- It reuses the :class:`~backend.schemas.common.UserRole` enum instead
  of redefining roles.
- It reuses :class:`~backend.exceptions.ValidationError` for invariant
  violations.
- Email-format and password-strength validation are intentionally *not*
  duplicated here — those belong to the API schema layer
  (:mod:`backend.schemas.auth`).  Only core domain invariants are
  enforced (see :meth:`User._validate`).

Contents:
    - :class:`User` — mutable application user record.

Usage::

    from backend.models import User

    user = User(username="admin", email="admin@visionops.ai")
    payload = user.to_dict()
    restored = User.from_dict(payload)
    user.update(is_active=False)
"""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from datetime import datetime, timezone
from typing import Any

from backend.exceptions import ValidationError
from backend.schemas.common import UserRole

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class User:
    """Application user record (mutable domain object).

    Represents the internally-held user metadata used by the
    authentication and authorization services.  Instances are
    intentionally **mutable** — user records are updated at runtime
    (role changes, deactivation, profile updates) — so ``frozen=True``
    is deliberately *not* applied.

    The dataclass provides structural equality and a readable ``repr``;
    instances are unhashable because they are mutable.

    Attributes:
        user_id: Unique user identifier.
        username: Unique username (3–50 chars in the schema layer).
        email: Optional email address (validated by the schema layer).
        role: User role (one of :class:`~backend.schemas.common.UserRole`).
        is_active: Whether the account is currently active.
        created_at: Timezone-aware UTC creation timestamp.
        updated_at: Optional timezone-aware UTC last-update timestamp.
    """

    user_id: str
    username: str
    email: str | None = None
    role: UserRole = UserRole.OPERATOR
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # ------------------------------------------------------------------
    # Construction / Validation
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        """Normalise role/timestamps and validate core invariants.

        The ``role`` value is coerced into a
        :class:`~backend.schemas.common.UserRole` member (matching the
        schema layer, which accepts raw role strings).  Timestamps are
        normalised to timezone-aware UTC (naive values are assumed to be
        UTC).  A missing ``created_at`` is set to the current UTC time.

        Raises:
            ValidationError: If any core invariant is violated.
        """
        self.role = self._coerce_role(self.role)
        self.created_at = self._coerce_datetime(self.created_at)
        self.updated_at = self._coerce_datetime(self.updated_at)
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        self._validate()

    def _validate(self) -> None:
        """Enforce the core domain invariants of a user record.

        Only fundamental invariants are checked here.  Email format,
        username pattern, and password strength are deliberately left to
        the API schema layer to avoid duplicated logic.

        Raises:
            ValidationError: If any invariant is violated.
        """
        if not isinstance(self.user_id, str) or not self.user_id.strip():
            raise ValidationError("User.user_id must be a non-empty string.")

        if not isinstance(self.username, str) or not self.username.strip():
            raise ValidationError("User.username must be a non-empty string.")

        if self.email is not None and not isinstance(self.email, str):
            raise ValidationError(
                f"User.email must be a string or None, got "
                f"{type(self.email).__name__}."
            )

        if not isinstance(self.role, UserRole):
            raise ValidationError(
                "User.role must be a UserRole enum member, got "
                f"{self.role!r}."
            )

        if not isinstance(self.is_active, bool):
            raise ValidationError(
                f"User.is_active must be a bool, got "
                f"{type(self.is_active).__name__}."
            )

        if self.created_at is None:
            raise ValidationError("User.created_at must not be None.")

        if (
            self.updated_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "User.updated_at must not be earlier than created_at."
            )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize the user record to a plain dictionary.

        Enum values are serialised to their string values and datetime
        fields to ISO 8601 strings so the output is JSON/CSV friendly.

        Returns:
            Dictionary mapping every field name to its value.
        """
        data: dict[str, Any] = {}
        for field_info in fields(self):
            value = getattr(self, field_info.name)
            if isinstance(value, UserRole):
                value = value.value
            elif isinstance(value, datetime):
                value = value.isoformat()
            data[field_info.name] = value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "User":
        """Build a :class:`User` instance from a plain dictionary.

        Unknown keys are ignored, keeping the helper tolerant of
        storage-layer records that may carry extra fields.  The ``role``
        value is coerced into a :class:`~backend.schemas.common.UserRole`
        member and timestamps are parsed from ISO 8601 strings and
        normalised to timezone-aware UTC.

        Args:
            data: Dictionary of user record values.

        Returns:
            A new :class:`User` instance.

        Raises:
            ValidationError: If ``role`` is invalid, a timestamp is
                malformed, or a core invariant is violated.
        """
        known = {field_info.name for field_info in fields(cls)}
        kwargs: dict[str, Any] = {}
        for key, value in data.items():
            if key not in known:
                continue
            kwargs[key] = value

        if "role" in kwargs:
            kwargs["role"] = cls._coerce_role(kwargs["role"])

        if "created_at" in kwargs:
            kwargs["created_at"] = cls._coerce_datetime(kwargs["created_at"])
        if "updated_at" in kwargs:
            kwargs["updated_at"] = cls._coerce_datetime(kwargs["updated_at"])

        return cls(**kwargs)

    # ------------------------------------------------------------------
    # Copy / Update
    # ------------------------------------------------------------------

    def copy(self) -> "User":
        """Return a shallow copy of this user record.

        The copy is re-validated on construction via
        :meth:`__post_init__`.

        Returns:
            A new :class:`User` instance with the same field values.
        """
        return replace(self)

    def update(self, **kwargs: Any) -> "User":
        """Apply field updates to this user record in place.

        Only declared fields may be updated; unknown field names raise
        :class:`~backend.exceptions.ValidationError`.  The ``role``
        value is coerced into a
        :class:`~backend.schemas.common.UserRole` member and timestamps
        are normalised to timezone-aware UTC.  Core domain invariants
        are re-validated after the updates are applied.

        Args:
            **kwargs: Field name/value pairs to apply.

        Returns:
            ``self`` to allow method chaining.

        Raises:
            ValidationError: If an unknown field is supplied, ``role``
                is invalid, or a core invariant is violated after the
                update.
        """
        known = {field_info.name for field_info in fields(self)}
        unknown = sorted(set(kwargs) - known)
        if unknown:
            raise ValidationError(
                f"Unknown user field(s): {', '.join(unknown)}."
            )

        if "role" in kwargs:
            kwargs["role"] = self._coerce_role(kwargs["role"])

        if "created_at" in kwargs:
            kwargs["created_at"] = self._coerce_datetime(kwargs["created_at"])
        if "updated_at" in kwargs:
            kwargs["updated_at"] = self._coerce_datetime(kwargs["updated_at"])

        for key, value in kwargs.items():
            setattr(self, key, value)

        self._validate()
        return self

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_role(value: str | UserRole) -> UserRole:
        """Coerce a raw role value into a :class:`UserRole` member.

        Args:
            value: Raw role value (enum member or string).

        Returns:
            The corresponding :class:`UserRole` member.

        Raises:
            ValidationError: If *value* is not a valid user role.
        """
        if isinstance(value, UserRole):
            return value
        try:
            return UserRole(value.strip().lower())
        except (AttributeError, ValueError) as exc:
            valid = ", ".join(sorted(r.value for r in UserRole))
            raise ValidationError(
                f"Invalid role {value!r}. Valid roles: {valid}."
            ) from exc

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

__all__ = ["User"]

