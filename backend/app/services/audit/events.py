"""Append-only activity log — who did what, not document contents."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from app.logging_context import get_request_id

logger = logging.getLogger("audit")

_memory_audit_events: list[dict[str, Any]] = []


def reset_memory_audit() -> None:
    """Clear in-memory audit events (tests only)."""
    _memory_audit_events.clear()


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
        logger.debug("Audit skip (supabase unavailable): %s", e)
        return None


async def log_audit(
    action: str,
    *,
    actor_user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """Record an audit action. Fails silently."""
    try:
        row: dict[str, Any] = {"action": action}
        rid = get_request_id()
        if rid and rid != "-":
            row["request_id"] = rid
        if actor_user_id:
            row["actor_user_id"] = actor_user_id
        if resource_type:
            row["resource_type"] = resource_type
        if resource_id:
            row["resource_id"] = str(resource_id)
        if metadata:
            row["metadata"] = metadata

        client = _supabase_client()
        if client is not None:
            client.table("audit_events").insert(row).execute()
        else:
            _memory_audit_events.append(
                {
                    **row,
                    "id": str(uuid4()),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            logger.debug("Audit (memory): %s", action)
    except Exception as e:
        logger.warning("Audit log failed: %s (action=%s)", e, action)
