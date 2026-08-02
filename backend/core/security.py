"""VisionOps AI — Core security helpers.

This module provides the low-level, dependency-light primitives for
password hashing and JWT creation/verification.  It is the shared
security foundation referenced by the service layer
(:mod:`backend.services.auth_service`) and authentication middleware.

The implementation prefers the optional third-party libraries
``PyJWT`` and ``bcrypt`` when they are installed, and otherwise falls
back to a stdlib-only implementation (``hashlib.pbkdf2_hmac`` and a
token format compatible with the rest of the backend).  This keeps
``backend.core`` importable and testable without hard third-party
runtime requirements.

Only *explicitly called* functions have side effects.  Importing this
module never touches the filesystem, never reads configuration beyond
the already-initialised :data:`~backend.core.config.settings` singleton,
and never starts any services.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from .config import settings

# ``backend.exceptions`` is importable when the package is loaded as
# ``backend.core``; when ``core`` is imported as a top-level package
# (e.g. when running from the ``backend/`` directory), fall back to the
# top-level ``exceptions`` package.
try:  # pragma: no cover - depends on import context
    from ..exceptions import AuthenticationError
except ImportError:  # pragma: no cover - top-level ``core`` package
    try:  # pragma: no cover
        from backend.exceptions import AuthenticationError  # type: ignore
    except ImportError:  # pragma: no cover
        from exceptions import AuthenticationError  # type: ignore

logger = logging.getLogger("visionops.core.security")

# ---------------------------------------------------------------------------
# Optional dependencies
# ---------------------------------------------------------------------------

try:  # pragma: no cover - depends on environment
    import jwt as _pyjwt  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    _pyjwt = None

try:  # pragma: no cover - depends on environment
    import bcrypt as _bcrypt  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    _bcrypt = None

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: The default JWT signing algorithm (overridable via settings).
_DEFAULT_ALGORITHM: str = "HS256"

#: The default token type claim.
_TOKEN_TYPE: str = "bearer"

#: The algorithm used for stdlib-only password hashing.
_PBKDF2_ALGORITHM: str = "pbkdf2_sha256"

#: Number of PBKDF2 iterations used for stdlib-only hashing.
_PBKDF2_ITERATIONS: int = 260_000

#: Salt length in bytes for stdlib-only hashing.
_SALT_BYTES: int = 16

#: Hash length in bytes for stdlib-only hashing.
_HASH_BYTES: int = 32

#: Prefix used to distinguish stdlib-only hashes.
_PBKDF2_PREFIX: str = "pbkdf2_sha256$"


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a plain-text password.

    Uses ``bcrypt`` when available; otherwise falls back to a
    stdlib-only PBKDF2-HMAC-SHA256 hash.

    Args:
        password: The plain-text password to hash.

    Returns:
        A string containing the hash.  The string is self-describing so
        :func:`verify_password` can detect the algorithm used.

    Raises:
        AuthenticationError: If *password* is empty or not a string.
    """
    if not password or not isinstance(password, str):
        raise AuthenticationError("Password must be a non-empty string.")

    if _bcrypt is not None:
        return _bcrypt.hashpw(
            password.encode("utf-8"), _bcrypt.gensalt()
        ).decode("utf-8")

    salt = secrets.token_bytes(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
        dklen=_HASH_BYTES,
    )
    encoded = base64.urlsafe_b64encode(dk).rstrip(b"=").decode("ascii")
    salt_b64 = base64.urlsafe_b64encode(salt).rstrip(b"=").decode("ascii")
    return f"{_PBKDF2_PREFIX}{_PBKDF2_ITERATIONS}${salt_b64}${encoded}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plain-text password against a stored hash.

    Args:
        password: The plain-text password to check.
        hashed: The stored hash produced by :func:`hash_password`.

    Returns:
        ``True`` if the password matches, ``False`` otherwise.

    Raises:
        AuthenticationError: If *password* is empty or *hashed* is
            malformed.
    """
    if not password or not isinstance(password, str):
        raise AuthenticationError("Password must be a non-empty string.")
    if not hashed or not isinstance(hashed, str):
        raise AuthenticationError("Hashed password must be a non-empty string.")

    try:
        # bcrypt format
        if hashed.startswith("$2"):
            if _bcrypt is not None:
                return _bcrypt.checkpw(
                    password.encode("utf-8"), hashed.encode("utf-8")
                )
            return False

        # PBKDF2 format
        if hashed.startswith(_PBKDF2_PREFIX):
            parts = hashed.split("$")
            if len(parts) != 4:
                return False
            _, iterations_str, salt_b64, expected_b64 = parts
            iterations = int(iterations_str)
            salt = base64.urlsafe_b64decode(
                salt_b64.encode("ascii") + b"=" * (-len(salt_b64) % 4)
            )
            expected = base64.urlsafe_b64decode(
                expected_b64.encode("ascii") + b"=" * (-len(expected_b64) % 4)
            )
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                iterations,
                dklen=len(expected),
            )
            return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

    return False


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def _secret_key() -> str:
    """Return the configured JWT secret key.

    Returns:
        The ``SECRET_KEY`` from settings.
    """
    return settings.SECRET_KEY


def create_access_token(
    subject: str,
    *,
    username: str | None = None,
    role: str | None = None,
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
    algorithm: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The user identifier (``sub`` claim).
        username: Optional username claim.
        role: Optional role claim.
        expires_delta: Token lifetime.  Defaults to the configured
            ``ACCESS_TOKEN_EXPIRE_MINUTES``.
        secret_key: Override for the JWT signing secret.  Defaults to
            ``settings.SECRET_KEY``.
        algorithm: JWT signing algorithm.  Defaults to
            ``settings.JWT_ALGORITHM`` or ``HS256``.
        extra_claims: Optional additional claims to embed.

    Returns:
        A signed JWT string.

    Raises:
        AuthenticationError: If *subject* is empty.
    """
    if not subject or not isinstance(subject, str):
        raise AuthenticationError("subject (user id) is required to create a token.")

    secret = secret_key or _secret_key()
    alg = algorithm or getattr(settings, "JWT_ALGORITHM", _DEFAULT_ALGORITHM)
    if not expires_delta:
        minutes = int(
            getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30)
        )
        expires_delta = timedelta(minutes=minutes)

    now = datetime.now(timezone.utc)
    expires_at = now + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        # NumericDate claims (Unix epoch seconds) — JSON-safe and JWT-compliant
        # regardless of whether PyJWT or the stdlib fallback is used.
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "type": _TOKEN_TYPE,
    }
    if username is not None:
        payload["username"] = username
    if role is not None:
        payload["role"] = role
    if extra_claims:
        payload.update(extra_claims)

    if _pyjwt is not None:
        return _pyjwt.encode(payload, secret, algorithm=alg)

    # Stdlib-only fallback: HMAC-SHA256 JWT-like token.
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64encode(json.dumps(header, separators=(",", ":")))
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")))
    signing_input = f"{header_b64}.{payload_b64}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    signature_b64 = _b64encode(signature)
    return f"{signing_input}.{signature_b64}"


def decode_token(
    token: str,
    *,
    secret_key: str | None = None,
    algorithm: str | None = None,
    verify_exp: bool = True,
) -> dict[str, Any]:
    """Decode and verify a JWT access token.

    Args:
        token: The JWT string.
        secret_key: Override for the JWT signing secret.  Defaults to
            ``settings.SECRET_KEY``.
        algorithm: Expected signing algorithm.
        verify_exp: Whether to enforce token expiry (default ``True``).

    Returns:
        The decoded token payload dictionary.

    Raises:
        AuthenticationError: If the token is malformed, expired, or its
            signature is invalid.
    """
    if not token or not isinstance(token, str):
        raise AuthenticationError("Token is required for verification.")

    secret = secret_key or _secret_key()
    alg = algorithm or getattr(settings, "JWT_ALGORITHM", _DEFAULT_ALGORITHM)

    if _pyjwt is not None:
        try:
            options = {"verify_exp": verify_exp}
            payload = _pyjwt.decode(
                token,
                secret,
                algorithms=[alg],
                options=options,
            )
        except _pyjwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Token has expired.") from exc
        except _pyjwt.InvalidTokenError as exc:
            raise AuthenticationError(
                f"Invalid token: {exc}"
            ) from exc
        return dict(payload)

    # Stdlib fallback
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthenticationError("Invalid token format.")
    header_b64, payload_b64, signature_b64 = parts

    signing_input = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(
        secret.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    try:
        provided_sig = _b64decode(signature_b64)
    except (ValueError, TypeError) as exc:
        raise AuthenticationError("Invalid token signature.") from exc
    if not hmac.compare_digest(expected_sig, provided_sig):
        raise AuthenticationError("Invalid token signature.")

    try:
        payload_raw = _b64decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_raw)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise AuthenticationError("Invalid token payload.") from exc

    if not isinstance(payload, dict):
        raise AuthenticationError("Invalid token payload.")

    if verify_exp and "exp" in payload:
        exp = payload["exp"]
        try:
            if isinstance(exp, (int, float)):
                exp_ts = float(exp)
            else:
                exp_ts = datetime.fromisoformat(str(exp)).timestamp()
        except (ValueError, TypeError):
            raise AuthenticationError("Invalid token expiry.")
        if exp_ts < time.time():
            raise AuthenticationError("Token has expired.")

    return dict(payload)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _b64encode(data: bytes | str) -> str:
    """URL-safe base64 encode bytes (or an encoded string)."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    """URL-safe base64 decode a string with padding restoration."""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data.encode("ascii") + padding.encode("ascii"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
]

