"""
Analytics event logging — track product usage for insights.

Events are written to Supabase analytics_events when configured,
otherwise kept in an in-memory list for local/dev.
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger("analytics")

_memory_analytics_events: list[dict[str, Any]] = []


def reset_memory_analytics() -> None:
    """Clear in-memory analytics events (tests only)."""
    _memory_analytics_events.clear()


@contextmanager
def track_duration():
    """Context manager that yields a dict with elapsed ms after the block."""
    start = time.monotonic()
    result = {"ms": 0}
    try:
        yield result
    finally:
        result["ms"] = int((time.monotonic() - start) * 1000)


def _supabase_client():
    from app.persistence.supabase_repository import (
        get_supabase_client,
        is_supabase_configured,
    )

    if not is_supabase_configured():
        return None
    try:
        return get_supabase_client()
    except Exception as e:
        logger.debug("Analytics skip (supabase unavailable): %s", e)
        return None


async def log_event(
    event_type: str,
    *,
    user_id: Optional[str] = None,
    template_id: Optional[str] = None,
    run_id: Optional[str] = None,
    duration_ms: Optional[int] = None,
    page_count: Optional[int] = None,
    error: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Log an analytics event. Fails silently."""
    try:
        row: dict[str, Any] = {"event_type": event_type}
        if user_id:
            row["user_id"] = user_id
        if template_id:
            row["template_id"] = template_id
        if run_id:
            row["run_id"] = run_id
        if duration_ms is not None:
            row["duration_ms"] = duration_ms
        if page_count is not None:
            row["page_count"] = page_count
        if error:
            row["error"] = error[:500]
        if metadata:
            row["metadata"] = metadata

        client = _supabase_client()
        if client is not None:
            client.table("analytics_events").insert(row).execute()
        else:
            _memory_analytics_events.append(
                {
                    **row,
                    "id": str(uuid4()),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            logger.debug("Analytics (memory): %s", event_type)
    except Exception as e:
        logger.warning("Analytics log failed: %s (event=%s)", e, event_type)
