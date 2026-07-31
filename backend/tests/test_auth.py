"""VisionOps AI — Unit tests for the ``auth`` API module and AuthService.

Tests:
- Auth API endpoint schemas
- AuthService: register, login, logout, JWT operations
- Password hashing
- Token validation (expired, invalid, refresh)
- Protected endpoint access
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from backend.exceptions import (
    AuthenticationError,
    RequiredFieldError,
    ValidationError,
)


# ===========================================================================
# Auth API Module
# ===========================================================================


class TestAuthAPIImports:
    """Verify auth-related modules are importable."""

    def test_auth_api_module(self):
        """The auth API module can be imported."""
        import backend.api.auth  # noqa: F401

    def test_auth_schemas_module(self):
        """The auth schema module can be imported."""
        import backend.schemas.auth  # noqa: F401

    def test_auth_service_module(self):
        """The auth_service module can be imported."""
        import backend.services.auth_service  # noqa: F401

    def test_user_model_module(self):
        """The user model module can be imported."""
        import backend.models.user  # noqa: F401


# ===========================================================================
# Auth Schemas
# ===========================================================================


class TestAuthSchemas:
    """Tests for auth-related Pydantic schemas."""

    def test_login_request_schema(self):
        """LoginRequest schema exists with username and password fields."""
        from backend.schemas.auth import LoginRequest

        assert hasattr(LoginRequest, "model_config") or hasattr(LoginRequest, "Config")

    def test_register_request_schema(self):
        """RegisterRequest schema exists."""
        from backend.schemas.auth import RegisterRequest

        assert RegisterRequest is not None

    def test_token_response_schema(self):
        """TokenResponse schema exists."""
        from backend.schemas.auth import TokenResponse

        assert TokenResponse is not None


# ===========================================================================
# AuthService — Password Operations
# ===========================================================================


class TestAuthServicePasswordOps:
    """Tests for AuthService password hashing and verification."""

    def test_hash_password_returns_string(self, mock_auth_service: MagicMock):
        """hash_password returns a non-empty string."""
        from backend.services.auth_service import AuthService

        service = AuthService()
        hashed = service.hash_password("test_password")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_password_empty_raises(self, mock_auth_service: MagicMock):
        """hash_password raises RequiredFieldError for empty password."""
        from backend.services.auth_service import AuthService

        service = AuthService()
        with pytest.raises(RequiredFieldError, match="Password"):
            service.hash_password("")

    def test_verify_password_correct(self, mock_auth_service: MagicMock):
        """verify_password returns True for matching passwords."""
        from backend.services.auth_service import AuthService

        service = AuthService()
        hashed = service.hash_password("test_password")
        assert service.verify_password("test_password", hashed) is True

    def test_verify_password_incorrect(self, mock_auth_service: MagicMock):
        """verify_password returns False for non-matching passwords."""
        from backend.services.auth_service import AuthService

        service = AuthService()
        hashed = service.hash_password("test_password")
        assert service.verify_password("wrong_password", hashed) is False

    def test_verify_password_empty_raises(self, mock_auth_service: MagicMock):
        """verify_password raises RequiredFieldError for empty password."""
        from backend.services.auth_service import AuthService

        service = AuthService()
        with pytest.raises(RequiredFieldError, match="Password"):
            service.verify_password("", "hashed_value")


# ===========================================================================
# AuthService — Registration
# ===========================================================================


class TestAuthServiceRegistration:
    """Tests for AuthService user registration."""

    def test_register_user_success(self, mock_storage_service: MagicMock):
        """register_user creates a new user record."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.return_value = []
        mock_storage_service.append_csv_store.return_value = MagicMock()
        service = AuthService(storage=mock_storage_service)

        result = service.register_user(
            username="newuser",
            password="newpass123",
            role="operator",
        )
        assert result["username"] == "newuser"
        assert result["role"] == "operator"
        assert "user_id" in result

    def test_register_user_duplicate(self, mock_storage_service: MagicMock):
        """register_user raises ValidationError for duplicate username."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.return_value = [
            {"username": "existing_user"},
        ]
        service = AuthService(storage=mock_storage_service)

        with pytest.raises(ValidationError, match="already exists"):
            service.register_user(
                username="existing_user",
                password="newpass123",
            )

    def test_register_user_empty_username(self, mock_storage_service: MagicMock):
        """register_user raises RequiredFieldError for empty username."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(RequiredFieldError, match="Username"):
            service.register_user(username="", password="pass")

    def test_register_user_short_password(self, mock_storage_service: MagicMock):
        """register_user raises ValidationError for short password."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="Password must be at least"):
            service.register_user(username="newuser", password="short")

    def test_register_user_invalid_role(self, mock_storage_service: MagicMock):
        """register_user raises ValidationError for invalid role."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(ValidationError, match="Invalid role"):
            service.register_user(
                username="newuser", password="validpass123", role="invalid_role",
            )


# ===========================================================================
# AuthService — Login / Logout
# ===========================================================================


class TestAuthServiceLoginLogout:
    """Tests for AuthService login and logout."""

    def test_login_success(self, mock_storage_service: MagicMock):
        """login returns token data for valid credentials."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.return_value = [
            {
                "user_id": "u1", "username": "admin", "password": "hashed_admin",
                "role": "admin", "is_active": "true",
            },
        ]
        service = AuthService(storage=mock_storage_service)

        with patch.object(service, "verify_password", return_value=True):
            result = service.login(username="admin", password="admin123")
        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert result["username"] == "admin"

    def test_login_user_not_found(self, mock_storage_service: MagicMock):
        """login raises AuthenticationError for non-existent user."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.return_value = []
        service = AuthService(storage=mock_storage_service)

        with pytest.raises(AuthenticationError, match="Invalid username or password"):
            service.login(username="nonexistent", password="pass")

    def test_login_inactive_user(self, mock_storage_service: MagicMock):
        """login raises AuthenticationError for inactive user."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.return_value = [
            {
                "user_id": "u1", "username": "inactive_user",
                "password": "hashed", "role": "operator",
                "is_active": "false",
            },
        ]
        service = AuthService(storage=mock_storage_service)

        with pytest.raises(AuthenticationError, match="inactive"):
            service.login(username="inactive_user", password="pass")

    def test_login_wrong_password(self, mock_storage_service: MagicMock):
        """login raises AuthenticationError for wrong password."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.return_value = [
            {
                "user_id": "u1", "username": "admin", "password": "hashed_pass",
                "role": "admin", "is_active": "true",
            },
        ]
        service = AuthService(storage=mock_storage_service)

        with patch.object(service, "verify_password", return_value=False):
            with pytest.raises(AuthenticationError, match="Invalid username or password"):
                service.login(username="admin", password="wrongpass")

    def test_logout_success(self, mock_storage_service: MagicMock):
        """logout returns success message."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        result = service.logout(user_id="u1")
        assert result["message"] == "Successfully logged out."


# ===========================================================================
# AuthService — JWT Operations
# ===========================================================================


class TestAuthServiceJWT:
    """Tests for AuthService JWT generation and validation."""

    def test_create_access_token_format(self, mock_storage_service: MagicMock):
        """create_access_token returns a three-part JWT."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        token = service.create_access_token(
            user_id="u1", username="admin", role="admin",
        )
        parts = token.split(".")
        assert len(parts) == 3

    def test_create_access_token_with_expiry(self, mock_storage_service: MagicMock):
        """create_access_token accepts custom expires_in."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        token = service.create_access_token(
            user_id="u1", username="admin", role="admin",
            expires_in=3600,
        )
        assert isinstance(token, str)

    def test_verify_token_valid(self, mock_storage_service: MagicMock):
        """verify_token returns payload for a valid token."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        token = service.create_access_token(
            user_id="u1", username="admin", role="admin",
        )
        payload = service.verify_token(token)
        assert payload["user_id"] == "u1"
        assert payload["username"] == "admin"
        assert payload["role"] == "admin"

    def test_verify_token_expired(self, mock_storage_service: MagicMock):
        """verify_token raises AuthenticationError for expired token."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        token = service.create_access_token(
            user_id="u1", username="admin", role="admin",
            expires_in=-1,
        )
        with pytest.raises(AuthenticationError, match="expired"):
            service.verify_token(token)

    def test_verify_token_invalid_signature(self, mock_storage_service: MagicMock):
        """verify_token raises AuthenticationError for invalid signature."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(AuthenticationError, match="Invalid token"):
            service.verify_token(
                "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoidTEifQ.invalid",
            )

    def test_verify_token_malformed(self, mock_storage_service: MagicMock):
        """verify_token raises AuthenticationError for malformed token."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(AuthenticationError, match="Invalid token format"):
            service.verify_token("not-a-valid-token")

    def test_refresh_token_valid(self, mock_storage_service: MagicMock):
        """refresh_token returns a new token for a valid token."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        token = service.create_access_token(
            user_id="u1", username="admin", role="admin",
        )
        result = service.refresh_token(token)
        assert "access_token" in result
        assert result["token_type"] == "bearer"
        assert result["expires_in"] > 0


# ===========================================================================
# AuthService — Protected Endpoints
# ===========================================================================


class TestAuthServiceProtectedEndpoints:
    """Tests for protected endpoint access control."""

    def test_check_admin_role(self, mock_storage_service: MagicMock):
        """check_role allows admin access."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        result = service.check_role(user_id="u1", required_role="admin")
        assert result["authorized"] is True

    def test_check_role_no_token(self, mock_storage_service: MagicMock):
        """check_role raises AuthenticationError without token."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(AuthenticationError, match="not authenticated"):
            service.check_role(user_id=None, required_role="admin")

    def test_check_role_insufficient(
        self,
        mock_storage_service: MagicMock,
    ):
        """check_role denies access for insufficient permissions."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.return_value = [
            {"user_id": "u1", "role": "operator"},
        ]
        service = AuthService(storage=mock_storage_service)
        with pytest.raises(AuthenticationError, match="Insufficient permissions"):
            service.check_role(user_id="u1", required_role="admin")


# ===========================================================================
# Edge Cases
# ===========================================================================


class TestAuthEdgeCases:
    """Edge-case tests for the auth layer."""

    def test_login_empty_body(self, mock_storage_service: MagicMock):
        """login raises RequiredFieldError for empty username and password."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        with pytest.raises(RequiredFieldError, match="Username"):
            service.login(username="", password="")

    def test_token_with_special_chars(self, mock_storage_service: MagicMock):
        """create_access_token handles special characters in username."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        token = service.create_access_token(
            user_id="u1",
            username="user@company.com",
            role="admin",
        )
        payload = service.verify_token(token)
        assert payload["username"] == "user@company.com"

    def test_token_with_unicode(self, mock_storage_service: MagicMock):
        """create_access_token handles unicode characters."""
        from backend.services.auth_service import AuthService

        service = AuthService(storage=mock_storage_service)
        token = service.create_access_token(
            user_id="u1",
            username="\u7528\u6237",
            role="admin",
        )
        payload = service.verify_token(token)
        assert payload["username"] == "\u7528\u6237"

    def test_authenticate_user_storage_failure_fallback(self, mock_storage_service: MagicMock):
        """authenticate_user falls back to default admin on storage failure."""
        from backend.services.auth_service import AuthService

        mock_storage_service.read_csv_store.side_effect = Exception("Storage unavailable")
        service = AuthService(storage=mock_storage_service)

        result = service.authenticate_user(username="admin", password="admin123")
        assert result["username"] == "admin"
        assert result["role"] == "admin"
