"""VisionOps AI — Authentication Schemas.

Pydantic v2 schemas for the authentication domain. These map directly to
the interfaces exposed by :mod:`backend.services.auth_service` and the
auth API endpoints.

Contents:
    - :class:`LoginRequest` — request body for user login.
    - :class:`LoginResponse` — successful login payload.
    - :class:`RegisterRequest` — request body for user registration.
    - :class:`RegisterResponse` — successful registration payload.
    - :class:`TokenResponse` — token issuance/refresh payload.
    - :class:`UserResponse` — user metadata payload.

Validation covers required fields, email format, password strength,
username rules, role enumeration, and token format basics.

Usage:
    from backend.schemas.auth import (
        LoginRequest, LoginResponse, RegisterRequest, RegisterResponse,
        TokenResponse, UserResponse,
    )
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import EmailStr, Field, field_validator, model_validator

from backend.schemas.common import BaseSchema, UserRole

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_USERNAME_PATTERN: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9_.-]+$")
_TOKEN_TYPE_BEARER: str = "bearer"
_MIN_PASSWORD_LENGTH: int = 8
_MAX_PASSWORD_LENGTH: int = 128


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


class LoginRequest(BaseSchema):
    """Request body for authenticating a user.

    Attributes:
        username: The user's username (non-empty, trimmed).
        password: The user's plain-text password (non-empty).

    Example:
        .. code-block:: json

            {
                "username": "admin",
                "password": "admin123"
            }
    """

    username: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="The user's username.",
            examples=["admin"],
        ),
    ]
    password: Annotated[
        str,
        Field(
            min_length=1,
            max_length=_MAX_PASSWORD_LENGTH,
            description="The user's plain-text password.",
            examples=["admin123"],
        ),
    ]

    @field_validator("username")
    @classmethod
    def _validate_username_present(cls, value: str) -> str:
        """Reject empty or whitespace-only usernames.

        Args:
            value: The raw username.

        Returns:
            The stripped username.

        Raises:
            ValueError: If the username is empty after stripping.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("Username is required for login.")
        return stripped

    @field_validator("password")
    @classmethod
    def _validate_password_present(cls, value: str) -> str:
        """Reject empty or whitespace-only passwords.

        Args:
            value: The raw password.

        Returns:
            The password as provided (passwords are never trimmed).

        Raises:
            ValueError: If the password is empty.
        """
        if not value:
            raise ValueError("Password is required for login.")
        return value


class LoginResponse(BaseSchema):
    """Successful login response payload.

    Mirrors the dictionary returned by
    :meth:`AuthService.authenticate_user
    <backend.services.auth_service.AuthService.authenticate_user>`.

    Attributes:
        access_token: JWT access token string.
        token_type: Token type (``"bearer"``).
        expires_in: Token lifetime in seconds.
        user_id: Authenticated user identifier.
        username: Authenticated username.
        role: Authenticated user role.
        message: Optional success message.
    """

    access_token: Annotated[
        str,
        Field(
            min_length=1,
            description="JWT access token.",
            examples=["eyJhbGciOiJIUzI1NiJ9..."],
        ),
    ]
    token_type: Annotated[
        str,
        Field(
            default=_TOKEN_TYPE_BEARER,
            description="Token type.",
            examples=["bearer"],
        ),
    ] = _TOKEN_TYPE_BEARER
    expires_in: Annotated[
        int,
        Field(
            gt=0,
            description="Token lifetime in seconds.",
            examples=[3600],
        ),
    ]
    user_id: Annotated[
        str,
        Field(min_length=1, description="Authenticated user identifier."),
    ]
    username: Annotated[
        str,
        Field(min_length=1, description="Authenticated username."),
    ]
    role: Annotated[
        UserRole,
        Field(description="Authenticated user role."),
    ] = UserRole.OPERATOR
    message: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional success message.",
            examples=["Login successful."],
        ),
    ] = None

    @field_validator("access_token", "user_id", "username")
    @classmethod
    def _reject_blank_token_fields(cls, value: str) -> str:
        """Reject empty token-related fields.

        Args:
            value: The raw field value.

        Returns:
            The stripped non-empty value.

        Raises:
            ValueError: If the value is empty/whitespace-only.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("Token fields must not be empty.")
        return stripped

    @field_validator("role", mode="before")
    @classmethod
    def _coerce_role(cls, value: str | UserRole) -> UserRole:
        """Coerce raw role strings into the :class:`UserRole` enum.

        Args:
            value: Raw role value.

        Returns:
            The corresponding enum member.

        Raises:
            ValueError: If the role is unknown.
        """
        if isinstance(value, UserRole):
            return value
        try:
            return UserRole(value.strip().lower())
        except ValueError:
            valid = ", ".join(sorted(r.value for r in UserRole))
            raise ValueError(
                f"Invalid role '{value}'. Valid roles: {valid}."
            ) from None


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class RegisterRequest(BaseSchema):
    """Request body for registering a new user.

    Attributes:
        username: Desired username (alphanumeric, dot, underscore, hyphen).
        email: User email address (validated format).
        password: Desired password (min length 8).
        role: Optional role assignment (default ``operator``).
    """

    username: Annotated[
        str,
        Field(
            min_length=3,
            max_length=50,
            pattern=r"^[a-zA-Z0-9_.-]+$",
            description=(
                "Username (3–50 chars; letters, digits, '.', '_', '-')."
            ),
            examples=["cold_chain_ops"],
        ),
    ]
    email: Annotated[
        EmailStr,
        Field(
            description="User email address.",
            examples=["operator@visionops.ai"],
        ),
    ]
    password: Annotated[
        str,
        Field(
            min_length=_MIN_PASSWORD_LENGTH,
            max_length=_MAX_PASSWORD_LENGTH,
            description=f"Password (min {_MIN_PASSWORD_LENGTH} characters).",
            examples=["SecurePass123"],
        ),
    ]
    role: Annotated[
        UserRole,
        Field(
            default=UserRole.OPERATOR,
            description="User role.",
        ),
    ] = UserRole.OPERATOR

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        """Validate username rules beyond the regex.

        Args:
            value: Raw username.

        Returns:
            The stripped username.

        Raises:
            ValueError: If the username is invalid.
        """
        stripped = value.strip()
        if len(stripped) < 3:
            raise ValueError("Username must be at least 3 characters.")
        if not _USERNAME_PATTERN.match(stripped):
            raise ValueError(
                "Username may only contain letters, digits, '.', '_', '-'."
            )
        return stripped

    @field_validator("password")
    @classmethod
    def _validate_password_strength(cls, value: str) -> str:
        """Validate basic password strength.

        Enforces a minimum length of 8 characters and at least one
        letter and one digit.

        Args:
            value: Raw password.

        Returns:
            The password as provided (never trimmed).

        Raises:
            ValueError: If the password is too weak.
        """
        if len(value) < _MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must be at least {_MIN_PASSWORD_LENGTH} characters."
            )
        if not any(ch.isalpha() for ch in value):
            raise ValueError("Password must contain at least one letter.")
        if not any(ch.isdigit() for ch in value):
            raise ValueError("Password must contain at least one digit.")
        return value

    @field_validator("role", mode="before")
    @classmethod
    def _coerce_registration_role(cls, value: str | UserRole) -> UserRole:
        """Coerce raw role strings into the :class:`UserRole` enum.

        Args:
            value: Raw role value.

        Returns:
            The corresponding enum member.

        Raises:
            ValueError: If the role is unknown.
        """
        if isinstance(value, UserRole):
            return value
        try:
            return UserRole(value.strip().lower())
        except ValueError:
            valid = ", ".join(sorted(r.value for r in UserRole))
            raise ValueError(
                f"Invalid role '{value}'. Valid roles: {valid}."
            ) from None


class RegisterResponse(BaseSchema):
    """Successful registration response payload.

    Attributes:
        user: The created :class:`UserResponse`.
        message: Optional confirmation message.
    """

    user: Annotated[
        "UserResponse",
        Field(description="The created user record."),
    ]
    message: Annotated[
        str,
        Field(
            default="User registered successfully.",
            description="Confirmation message.",
        ),
    ] = "User registered successfully."


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------


class TokenResponse(BaseSchema):
    """Token payload returned on login, refresh, or token issuance.

    Attributes:
        access_token: JWT access token string.
        token_type: Token type (``"bearer"``).
        expires_in: Token lifetime in seconds.
        refresh_token: Optional refresh token string.
        user_id: Optional user identifier.
        username: Optional username.
        role: Optional user role.
    """

    access_token: Annotated[
        str,
        Field(
            min_length=1,
            description="JWT access token.",
            examples=["eyJhbGciOiJIUzI1NiJ9..."],
        ),
    ]
    token_type: Annotated[
        str,
        Field(
            default=_TOKEN_TYPE_BEARER,
            description="Token type.",
            examples=["bearer"],
        ),
    ] = _TOKEN_TYPE_BEARER
    expires_in: Annotated[
        int,
        Field(
            gt=0,
            description="Token lifetime in seconds.",
            examples=[3600],
        ),
    ]
    refresh_token: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional refresh token.",
        ),
    ] = None
    user_id: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional user identifier.",
        ),
    ] = None
    username: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional username.",
        ),
    ] = None
    role: Annotated[
        UserRole | None,
        Field(
            default=None,
            description="Optional user role.",
        ),
    ] = None

    @field_validator("access_token")
    @classmethod
    def _access_token_not_empty(cls, value: str) -> str:
        """Reject empty access tokens.

        Args:
            value: The access token string.

        Returns:
            The stripped non-empty token.

        Raises:
            ValueError: If the token is empty.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("access_token must not be empty.")
        return stripped

    @field_validator("token_type")
    @classmethod
    def _token_type_bearer(cls, value: str) -> str:
        """Normalize token type to lowercase ``bearer``.

        Args:
            value: The token type string.

        Returns:
            Lowercased token type.

        Raises:
            ValueError: If the token type is empty.
        """
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("token_type must not be empty.")
        return normalized

    @field_validator("role", mode="before")
    @classmethod
    def _coerce_token_role(cls, value: str | UserRole | None) -> UserRole | None:
        """Coerce optional raw role into the :class:`UserRole` enum.

        Args:
            value: Optional raw role value.

        Returns:
            The enum member or ``None``.

        Raises:
            ValueError: If the role is unknown.
        """
        if value is None or isinstance(value, UserRole):
            return value
        try:
            return UserRole(value.strip().lower())
        except ValueError:
            valid = ", ".join(sorted(r.value for r in UserRole))
            raise ValueError(
                f"Invalid role '{value}'. Valid roles: {valid}."
            ) from None


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class UserResponse(BaseSchema):
    """User metadata payload returned to clients.

    Matches the user record shape produced by
    :meth:`AuthService.authenticate_user
    <backend.services.auth_service.AuthService.authenticate_user>` and the
    default users bootstrap in :mod:`backend.services.auth_service`.

    Attributes:
        user_id: Unique user identifier.
        username: Username.
        email: Optional email address.
        role: User role.
        is_active: Whether the account is active.
        created_at: ISO-8601 creation timestamp.
        updated_at: Optional ISO-8601 last-update timestamp.
    """

    user_id: Annotated[
        str,
        Field(min_length=1, description="Unique user identifier."),
    ]
    username: Annotated[
        str,
        Field(min_length=1, max_length=100, description="Username."),
    ]
    email: Annotated[
        EmailStr | None,
        Field(
            default=None,
            description="Optional user email.",
        ),
    ] = None
    role: Annotated[
        UserRole,
        Field(default=UserRole.OPERATOR, description="User role."),
    ] = UserRole.OPERATOR
    is_active: Annotated[
        bool,
        Field(default=True, description="Whether the account is active."),
    ] = True
    created_at: Annotated[
        datetime,
        Field(description="ISO-8601 creation timestamp."),
    ]
    updated_at: Annotated[
        datetime | None,
        Field(
            default=None,
            description="Optional ISO-8601 last-update timestamp.",
        ),
    ] = None

    @field_validator("user_id", "username")
    @classmethod
    def _reject_blank_user_fields(cls, value: str) -> str:
        """Reject empty user identifier/username.

        Args:
            value: The raw field value.

        Returns:
            The stripped non-empty value.

        Raises:
            ValueError: If the value is empty/whitespace-only.
        """
        stripped = value.strip()
        if not stripped:
            raise ValueError("User fields must not be empty.")
        return stripped

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _normalize_optional_timestamps(
        cls, value: datetime | str | None
    ) -> datetime | None:
        """Normalize naive datetimes to timezone-aware UTC.

        Args:
            value: Raw timestamp or ``None``.

        Returns:
            UTC-aware datetime or ``None``.
        """
        if value is None:
            return None
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            parsed = value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @field_validator("role", mode="before")
    @classmethod
    def _coerce_user_role(cls, value: str | UserRole) -> UserRole:
        """Coerce raw role strings into the :class:`UserRole` enum.

        Args:
            value: Raw role value.

        Returns:
            The corresponding enum member.

        Raises:
            ValueError: If the role is unknown.
        """
        if isinstance(value, UserRole):
            return value
        try:
            return UserRole(value.strip().lower())
        except ValueError:
            valid = ", ".join(sorted(r.value for r in UserRole))
            raise ValueError(
                f"Invalid role '{value}'. Valid roles: {valid}."
            ) from None

    @model_validator(mode="after")
    def _validate_updated_after_created(self) -> "UserResponse":
        """Ensure ``updated_at`` is not earlier than ``created_at``.

        Returns:
            The validated instance.

        Raises:
            ValueError: If *updated_at* precedes *created_at*.
        """
        if self.updated_at is not None and self.updated_at < self.created_at:
            raise ValueError(
                "updated_at must not be earlier than created_at."
            )
        return self


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "LoginRequest",
    "LoginResponse",
    "RegisterRequest",
    "RegisterResponse",
    "TokenResponse",
    "UserResponse",
]

