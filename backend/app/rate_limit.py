"""Shared rate limiter — per-user for authenticated routes, per-IP for public."""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _user_id_from_request(request: Request) -> str | None:
    """Resolve user id for rate limiting (works before route deps run)."""
    user = getattr(request.state, "current_user", None)
    if user and hasattr(user, "user_id") and user.user_id:
        return str(user.user_id)

    token: str | None = None
    auth = request.headers.get("Authorization") or ""
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip() or None
    if not token:
        token = request.query_params.get("access_token")

    if not token:
        return None

    try:
        from app.services.auth.jwt import decode_access_token

        payload = decode_access_token(token)
        sub = payload.get("sub")
        return str(sub) if sub else None
    except Exception:
        return None


def _get_rate_limit_key(request: Request) -> str:
    """Use JWT user_id when present, otherwise fall back to IP."""
    user_id = _user_id_from_request(request)
    if user_id:
        return f"user:{user_id}"
    return get_remote_address(request)


limiter = Limiter(key_func=_get_rate_limit_key)
