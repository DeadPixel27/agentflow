"""
Auth provider registry — maps config → implementation.

To add Supabase Auth later:
  1. Create services/auth/supabase_provider.py
  2. Register in _AUTH_PROVIDERS below
  3. Set AUTH_BACKEND=supabase in .env
"""

import logging

from app.config import settings
from app.persistence.protocols import DataRepository
from app.services.auth.email_provider import EmailAuthProvider
from app.services.auth.protocols import AuthProvider

logger = logging.getLogger("auth")

_AUTH_PROVIDERS: dict[str, type[EmailAuthProvider]] = {
    "email": EmailAuthProvider,
    # "supabase": SupabaseAuthProvider,  # future
}


def _resolve_backend() -> str:
    mode = settings.auth_backend.lower()
    if mode not in _AUTH_PROVIDERS:
        logger.warning("Unknown AUTH_BACKEND=%s — using email", mode)
        return "email"
    return mode


def get_auth_provider(repo: DataRepository) -> AuthProvider:
    """Return the configured auth provider for this request."""
    backend = _resolve_backend()
    return _AUTH_PROVIDERS[backend](repo)
