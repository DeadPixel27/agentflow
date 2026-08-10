"""Verify Google Identity Services ID tokens."""

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.config import settings


class InvalidGoogleTokenError(Exception):
    """Raised when a Google ID token is missing, invalid, or unverified."""


def verify_google_id_token(token: str) -> dict[str, str]:
    """
    Verify a Google ID token and return {"email", "name"}.

    Raises InvalidGoogleTokenError on failure.
    """
    if not token or not token.strip():
        raise InvalidGoogleTokenError("ID token is required")

    client_id = settings.google_client_id.strip()
    if not client_id:
        raise InvalidGoogleTokenError("GOOGLE_CLIENT_ID is not configured")

    try:
        idinfo = id_token.verify_oauth2_token(
            token.strip(),
            google_requests.Request(),
            client_id,
        )
    except ValueError as e:
        raise InvalidGoogleTokenError(f"Invalid Google ID token: {e}") from e

    iss = idinfo.get("iss")
    if iss not in ("accounts.google.com", "https://accounts.google.com"):
        raise InvalidGoogleTokenError("Invalid token issuer")

    if not idinfo.get("email_verified"):
        raise InvalidGoogleTokenError("Google email is not verified")

    email = (idinfo.get("email") or "").strip()
    if not email:
        raise InvalidGoogleTokenError("Token missing email")

    name = (idinfo.get("name") or "").strip() or email.split("@", 1)[0]
    return {"email": email, "name": name}
