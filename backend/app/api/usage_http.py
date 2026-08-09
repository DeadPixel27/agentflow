"""HTTP helpers for usage limits (shared by runs / workflows / extract)."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

from app.services.analytics.events import log_event
from app.services.usage.metering import (
    GlobalCapError,
    UsageLimitError,
    check_usage_allowed,
    record_usage,
)
from app.services.usage.page_count import count_upload_pages

logger = logging.getLogger("api")


async def enforce_usage(user_id: str, page_count: int = 1) -> None:
    """Raise 429 / 503 if the user or global cap would be exceeded."""
    try:
        await check_usage_allowed(user_id, page_count)
    except UsageLimitError as e:
        raise HTTPException(status_code=429, detail=str(e)) from e
    except GlobalCapError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


async def enforce_upload_usage(user_id: str, upload_id: str) -> int:
    """Count pages in an upload, enforce caps, return page_count."""
    page_count = await count_upload_pages(upload_id)
    await enforce_usage(user_id, page_count)
    return page_count


async def record_run_usage(
    user_id: str,
    *,
    page_count: int,
    run_id: Optional[str] = None,
    template_id: Optional[str] = None,
    event_type: str = "extraction",
) -> None:
    """Record usage + run_started analytics (best-effort)."""
    try:
        await record_usage(
            user_id,
            page_count,
            template_id=template_id,
            run_id=run_id,
            event_type=event_type,
        )
        await log_event(
            "run_started",
            user_id=user_id,
            template_id=template_id,
            run_id=run_id,
            page_count=page_count,
        )
    except Exception as e:
        logger.warning("Failed to record usage/analytics: %s", e)


async def record_extract_usage(
    user_id: str,
    *,
    page_count: int,
    event_type: str = "extract_api",
) -> None:
    """Record usage for direct extract endpoints (best-effort)."""
    try:
        await record_usage(user_id, page_count, event_type=event_type)
        await log_event(
            "extract_completed",
            user_id=user_id,
            page_count=page_count,
        )
    except Exception as e:
        logger.warning("Failed to record extract usage/analytics: %s", e)
