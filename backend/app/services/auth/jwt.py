"""
JWT token creation and validation.

Tokens contain user_id, email, and expiry. Used by the auth dependency
to identify the current user on every protected request.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger("auth")


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid, expired, or malformed."""


def create_access_token(
    user_id: str,
    email: str,
    *,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    if not settings.jwt_secret_key:
        raise RuntimeError(
            "JWT_SECRET_KEY is not set. Generate one with: "
            "python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(hours=settings.jwt_expiry_hours))

    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT token. Returns the payload dict.

    Raises InvalidTokenError if the token is expired, malformed, or invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError("Token missing user_id (sub)")
        return payload
    except JWTError as e:
        logger.warning("JWT decode failed: %s", e)
        raise InvalidTokenError(f"Invalid token: {e}") from e
