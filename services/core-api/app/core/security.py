"""Security, password hashing, and JWT token management for PaperLedger."""

from datetime import datetime, timedelta, timezone
from typing import Any
import uuid
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
import jwt

from app.core.config import get_settings
from app.core.errors import AuthenticationError

# Standard Argon2id configuration with memory-hard parameters
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(plain_password: str) -> str:
    """Hash a plain text password using Argon2id."""
    if not plain_password:
        raise ValueError("Password cannot be empty")
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against an Argon2id hash.

    Protected against timing attacks. Returns False for invalid hashes or mismatched passwords.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(
    subject: str | uuid.UUID,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Generate a signed JWT access token for user authentication."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    claims: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }

    if extra_claims:
        claims.update(extra_claims)

    encoded_jwt = jwt.encode(
        claims,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a signed JWT access token.

    Raises:
        AuthenticationError: If token is expired, invalid, or missing claims.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Enforce required standard claims
        if not payload.get("sub"):
            raise AuthenticationError(
                detail="Token payload is missing subject identifier ('sub')",
                error_type="urn:error:invalid-token",
            )

        if payload.get("type") != "access":
            raise AuthenticationError(
                detail="Invalid token type (expected 'access')",
                error_type="urn:error:invalid-token",
            )

        return payload

    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError(
            detail="Authentication token has expired. Please log in again.",
            error_type="urn:error:token-expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError(
            detail="Authentication token is malformed or signature is invalid.",
            error_type="urn:error:invalid-token",
        ) from exc
