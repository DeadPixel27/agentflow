"""Supabase client — returns None when not configured."""

import logging
from typing import Optional

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
