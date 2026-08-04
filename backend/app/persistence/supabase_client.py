"""Supabase connection helpers."""

import logging
from typing import Optional, Tuple

from supabase import Client, create_client

from app.config import settings

logger = logging.getLogger("db")

_client: Optional[Client] = None


def is_supabase_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_secret_key)


def get_supabase() -> Optional[Client]:
    global _client
    if not is_supabase_configured():
        return None
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_secret_key)
        logger.info("Supabase client initialized")
    return _client


def check_supabase_connection() -> Tuple[bool, str]:
    """
    Ping Supabase. Returns (ok, detail).
    detail: connected | not_configured | <error message>
    """
    if not is_supabase_configured():
        return False, "not_configured"

    try:
        client = get_supabase()
        if client is None:
            return False, "client_unavailable"
        client.table("users").select("id").limit(1).execute()
        return True, "connected"
    except Exception as e:
        logger.warning("Supabase health check failed: %s", e)
        return False, str(e)
