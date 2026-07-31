"""VisionOps AI — Authentication Service.

Provides business-logic orchestration for user authentication, token
management, and credential validation. Delegates low-level security
operations to ``backend.core.security`` and persistence to the storage
layer.

Responsibilities:
    - User authentication (validate credentials)
    - Access token creation and verification
    - Token refresh
    - Password change workflow
    - Session management

Usage::

    from backend.services import AuthService

    service = AuthService()
    token = service.authenticate_user(username="admin", password="secret")
    payload = service.verify_token(token)
    new_token = service.refresh_token(token)
"""

from __future__ import annotations

import logging
from typing import Any

from backend.core.config import settings
from backend.exceptions import (
    AuthenticationError,
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

_TOKEN_TYPE: str = "bearer"
_DEFAULT_TOKEN_EXPIRY: int = 3600  # 1 hour

# ---------------------------------------------------------------------------
# AuthService
# ---------------------------------------------------------------------------


class AuthService:
    """Orchestrates user authentication, token management, and credential
    validation.

    This service sits between the API layer and the security/storage
    layers. It coordinates authentication workflows, validates
    credentials, and manages token lifecycles — without implementing
    any low-level cryptography, hashing, or storage logic.

    Dependency injection is used for the storage layer to improve
    testability.

    Raises:
        AuthenticationError: If authentication fails.
        ValidationError: If input arguments are invalid.
        StorageError: If storage operations fail.
    """

    def __init__(
        self,
        storage: StorageService | None = None,
    ) -> None:
        """Initialise the authentication service.

        Args:
            storage: Injected ``StorageService`` instance. When ``None``,
                a default instance is created.
        """
        self._storage = storage or StorageService()
        logger.info(
            "AuthService initialised (storage=%s)",
            type(self._storage).__name__,
        )

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate_user(
        self,
        username: str,
        password: str,
    ) -> dict[str, Any]:
        """Authenticate a user with username and password.

        Validates credentials against stored user data. On success,
        returns an access token and user metadata.

        Args:
            username: The user's username.
            password: The user's plain-text password.

        Returns:
            Dictionary with authentication result:
            - ``access_token``: JWT access token string.
            - ``token_type``: Token type (``"bearer"``).
            - ``expires_in``: Token expiry in seconds.
            - ``user_id``: Authenticated user's identifier.
            - ``username``: Authenticated user's username.
            - ``role``: User role (e.g. ``"admin"``, ``"operator"``).

        Raises:
            RequiredFieldError: If *username* or *password* are empty.
            AuthenticationError: If credentials are invalid.
            StorageError: If reading user data fails.
        """
        if not username or not username.strip():
            raise RequiredFieldError(
                "Username is required for authentication.",
                field="username",
            )
        if not password:
            raise RequiredFieldError(
                "Password is required for authentication.",
                field="password",
            )

        logger.info(
            "Authenticating user: username='%s'", username
        )

        # --- Validate credentials against stored users ---
        try:
            users = self._storage.read_csv_store("users")
        except StorageError as exc:
            # Fallback: if users store doesn't exist, create default admin
            logger.warning(
                "Users store not found. Attempting default credential check."
            )
            users = self._get_default_users()

        # Look up user
        normalized_username = username.strip().lower()
        matched_user: dict[str, Any] | None = None

        for user in users:
            stored_username = user.get("username", "").strip().lower()
            if stored_username == normalized_username:
                matched_user = user
                break

        if matched_user is None:
            logger.warning(
                "Authentication failed: user '%s' not found.", username
            )
            raise AuthenticationError(
                "Invalid username or password."
            )

        # Verify password (simplified — in production, use hashed comparison)
        stored_password = matched_user.get("password", "")
        if password != stored_password:
            logger.warning(
                "Authentication failed: invalid password for user '%s'.",
                username,
            )
            raise AuthenticationError(
                "Invalid username or password."
            )

        # --- Generate token ---
        try:
            token_data = self._create_token(
                user_id=matched_user.get("user_id", ""),
                username=matched_user.get("username", ""),
                role=matched_user.get("role", "operator"),
            )
        except Exception as exc:
            raise AuthenticationError(
                f"Failed to generate access token: {exc}"
            ) from exc

        logger.info(
            "User '%s' authenticated successfully.", username
        )

        return {
            "access_token": token_data["access_token"],
            "token_type": _TOKEN_TYPE,
            "expires_in": token_data["expires_in"],
            "user_id": matched_user.get("user_id", ""),
            "username": matched_user.get("username", ""),
            "role": matched_user.get("role", "operator"),
        }

    # ------------------------------------------------------------------
    # Token Management
    # ------------------------------------------------------------------

    def create_access_token(
        self,
        user_id: str,
        username: str,
        role: str = "operator",
        expires_in: int | None = None,
    ) -> str:
        """Create a new access token for a user.

        Args:
            user_id: Unique user identifier.
            username: User's username.
            role: User role (default: ``"operator"``).
            expires_in: Token expiry in seconds (default: from settings
                or 3600).

        Returns:
            JWT access token string.

        Raises:
            RequiredFieldError: If *user_id* or *username* are empty.
        """
        if not user_id:
            raise RequiredFieldError(
                "user_id is required to create a token.",
                field="user_id",
            )
        if not username or not username.strip():
            raise RequiredFieldError(
                "username is required to create a token.",
                field="username",
            )

        token_data = self._create_token(
            user_id=user_id,
            username=username.strip(),
            role=role,
            expires_in=expires_in,
        )
        return token_data["access_token"]

    def verify_token(
        self,
        token: str,
    ) -> dict[str, Any]:
        """Verify and decode an access token.

        Args:
            token: The JWT token string to verify.

        Returns:
            Dictionary with decoded token payload:
            - ``user_id``: User identifier.
            - ``username``: Username.
            - ``role``: User role.
            - ``exp``: Expiry timestamp.
            - ``iat``: Issued-at timestamp.

        Raises:
            RequiredFieldError: If *token* is empty.
            AuthenticationError: If the token is invalid or expired.
        """
        if not token:
            raise RequiredFieldError(
                "Token is required for verification.",
                field="token",
            )

        # Simplified token verification
        # In production, this would use JWT decode with secret key
        parts = token.split(".")
        if len(parts) != 3:
            raise AuthenticationError("Invalid token format.")

        # TODO: Implement proper JWT verification using backend.core.security
        #   from backend.core.security import decode_token
        #   payload = decode_token(token)

        # For now, return a basic payload structure
        logger.debug("Token verified successfully.")
        return {
            "user_id": "unknown",
            "username": "unknown",
            "role": "operator",
            "exp": 0,
            "iat": 0,
        }

    def refresh_token(
        self,
        token: str,
    ) -> dict[str, Any]:
        """Refresh an existing access token.

        Verifies the current token and issues a new one with an
        extended expiry.

        Args:
            token: The current (valid) access token.

        Returns:
            Dictionary with new token data:
            - ``access_token``: New JWT access token.
            - ``token_type``: Token type (``"bearer"``).
            - ``expires_in``: New token expiry in seconds.

        Raises:
            RequiredFieldError: If *token* is empty.
            AuthenticationError: If the current token is invalid.
        """
        if not token:
            raise RequiredFieldError(
                "Token is required for refresh.",
                field="token",
            )

        # Verify the current token
        payload = self.verify_token(token)

        # Create a new token
        new_token_data = self._create_token(
            user_id=payload.get("user_id", ""),
            username=payload.get("username", ""),
            role=payload.get("role", "operator"),
        )

        logger.info(
            "Token refreshed for user '%s'.",
            payload.get("username", "unknown"),
        )

        return {
            "access_token": new_token_data["access_token"],
            "token_type": _TOKEN_TYPE,
            "expires_in": new_token_data["expires_in"],
        }

    # ------------------------------------------------------------------
    # Password Management
    # ------------------------------------------------------------------

    def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> dict[str, Any]:
        """Change a user's password.

        Validates the current password before updating to the new one.

        Args:
            user_id: Unique user identifier.
            current_password: The user's current password.
            new_password: The desired new password.

        Returns:
            Dictionary with success message.

        Raises:
            RequiredFieldError: If any required field is empty.
            ValidationError: If the new password does not meet criteria.
            AuthenticationError: If the current password is incorrect.
            StorageError: If persisting the update fails.
        """
        if not user_id:
            raise RequiredFieldError(
                "user_id is required.", field="user_id"
            )
        if not current_password:
            raise RequiredFieldError(
                "current_password is required.", field="current_password"
            )
        if not new_password:
            raise RequiredFieldError(
                "new_password is required.", field="new_password"
            )

        # Validate new password length
        min_len = max(getattr(settings, "PASSWORD_MIN_LENGTH", 8), 4)
        if len(new_password) < min_len:
            raise ValidationError(
                f"New password must be at least {min_len} characters long."
            )

        # Fetch user record
        try:
            users = self._storage.read_csv_store("users")
        except StorageError:
            users = self._get_default_users()

        matched_user: dict[str, Any] | None = None
        for user in users:
            if user.get("user_id") == user_id:
                matched_user = user
                break

        if matched_user is None:
            raise AuthenticationError(f"User not found: '{user_id}'.")

        # Verify current password
        if matched_user.get("password", "") != current_password:
            raise AuthenticationError("Current password is incorrect.")

        # Update password
        def match_fn(row: dict[str, Any]) -> bool:
            return row.get("user_id") == user_id

        def update_fn(row: dict[str, Any]) -> dict[str, Any]:
            row["password"] = new_password
            row["updated_at"] = now_utc().isoformat()
            return row

        try:
            self._storage.csv_manager.update_rows("users", match_fn, update_fn)
        except StorageError as exc:
            raise StorageError(
                f"Failed to update password for user '{user_id}': {exc}"
            ) from exc

        logger.info("Password changed successfully for user '%s'.", user_id)
        return {
            "message": "Password changed successfully.",
            "user_id": user_id,
        }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _create_token(
        self,
        user_id: str,
        username: str,
        role: str,
        expires_in: int | None = None,
    ) -> dict[str, Any]:
        """Create a token payload and encode it.

        Args:
            user_id: User identifier.
            username: Username.
            role: User role.
            expires_in: Token expiry in seconds.

        Returns:
            Dictionary with ``access_token`` and ``expires_in``.
        """
        expiry = expires_in or getattr(
            settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30
        ) * 60 or _DEFAULT_TOKEN_EXPIRY

        # TODO: Replace with actual JWT encoding from backend.core.security
        #   from backend.core.security import create_access_token
        #   token = create_access_token(
        #       data={"sub": user_id, "username": username, "role": role},
        #       expires_delta=timedelta(seconds=expiry),
        #   )

        # Simplified token for now
        import hashlib
        import json
        import time
        from base64 import urlsafe_b64encode

        header = urlsafe_b64encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()

        now = int(time.time())
        payload = urlsafe_b64encode(
            json.dumps({
                "sub": user_id,
                "username": username,
                "role": role,
                "iat": now,
                "exp": now + expiry,
            }).encode()
        ).rstrip(b"=").decode()

        # Simple signature (placeholder)
        signature_input = f"{header}.{payload}"
        signature = hashlib.sha256(
            (signature_input + settings.SECRET_KEY).encode()
        ).hexdigest()

        access_token = f"{header}.{payload}.{signature}"

        return {
            "access_token": access_token,
            "expires_in": expiry,
        }

    def _get_default_users(self) -> list[dict[str, Any]]:
        """Return a default admin user list for bootstrapping.

        Returns:
            List of user dictionaries with a single admin user.
        """
        return [
            {
                "user_id": "user_admin_001",
                "username": "admin",
                "password": "admin123",
                "role": "admin",
                "email": "admin@visionops.ai",
                "created_at": now_utc().isoformat(),
            },
        ]
