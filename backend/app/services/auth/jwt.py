"""
JWT token creation and validation.

Session tokens contain user_id, email, and expiry (Bearer only).
Document tokens are short-lived capability JWTs scoped to one file
(safe to put in query strings for <img>/<iframe>).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger("auth")

DOCUMENT_TOKEN_PURPOSE = "doc"


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid, expired, or malformed."""


def _require_jwt_secret() -> None:
    if not settings.jwt_secret_key:
        raise RuntimeError(
            "JWT_SECRET_KEY is not set. Generate one with: "
            "python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )


def create_access_token(
    user_id: str,
    email: str,
    *,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token (session — Bearer only)."""
    _require_jwt_secret()

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
    Decode and validate a session JWT. Returns the payload dict.

    Raises InvalidTokenError if the token is expired, malformed, or invalid.
    Rejects document capability tokens (purpose=doc).
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
        if payload.get("purpose") == DOCUMENT_TOKEN_PURPOSE:
            raise InvalidTokenError("Document token cannot be used as a session token")
        return payload
    except JWTError as e:
        logger.warning("JWT decode failed: %s", e)
        raise InvalidTokenError(f"Invalid token: {e}") from e


def create_document_access_token(
    user_id: str,
    upload_id: str,
    document_id: str,
    *,
    expires_delta: Optional[timedelta] = None,
) -> tuple[str, datetime]:
    """
    Create a short-lived document capability token.

    Returns (token, expires_at_utc). Scoped to one upload/document pair.
    """
    _require_jwt_secret()

    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        or timedelta(minutes=settings.document_token_expiry_minutes)
    )

    payload = {
        "sub": user_id,
        "upload_id": upload_id,
        "document_id": document_id,
        "purpose": DOCUMENT_TOKEN_PURPOSE,
        "iat": now,
        "exp": expire,
    }

    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return token, expire


def decode_document_access_token(
    token: str,
    *,
    upload_id: str,
    document_id: str,
) -> dict:
    """
    Decode a document capability token and assert it matches the path.

    Returns payload with user_id (sub). Raises InvalidTokenError on mismatch.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as e:
        logger.warning("Document JWT decode failed: %s", e)
        raise InvalidTokenError(f"Invalid document token: {e}") from e

    if payload.get("purpose") != DOCUMENT_TOKEN_PURPOSE:
        raise InvalidTokenError("Not a document access token")

    user_id = payload.get("sub")
    if not user_id:
        raise InvalidTokenError("Document token missing user_id (sub)")

    if payload.get("upload_id") != upload_id:
        raise InvalidTokenError("Document token upload_id mismatch")
    if payload.get("document_id") != document_id:
        raise InvalidTokenError("Document token document_id mismatch")

    return {
        "user_id": str(user_id),
        "upload_id": str(payload["upload_id"]),
        "document_id": str(payload["document_id"]),
    }
