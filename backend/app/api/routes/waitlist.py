"""Waitlist route — collect Pro tier interest. No auth required."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

logger = logging.getLogger("api")

router = APIRouter(prefix="/api/waitlist", tags=["waitlist"])

_memory_waitlist: list[dict[str, Any]] = []


def reset_memory_waitlist() -> None:
    """Clear in-memory waitlist (tests only)."""
    _memory_waitlist.clear()


class WaitlistRequest(BaseModel):
    email: EmailStr
    name: str = ""
    source: str = "pricing_page"


class WaitlistResponse(BaseModel):
    message: str
    already_joined: bool = False


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
        logger.warning("Supabase unavailable for waitlist: %s", e)
        return None


@router.post("", response_model=WaitlistResponse)
async def join_waitlist(body: WaitlistRequest) -> WaitlistResponse:
    """Add an email to the Pro waitlist. No authentication required."""
    email = str(body.email).strip().lower()
    try:
        client = _supabase_client()

        if client is None:
            for entry in _memory_waitlist:
                if entry.get("email") == email:
                    return WaitlistResponse(
                        message="You're already on the waitlist! We'll reach out soon.",
                        already_joined=True,
                    )
            _memory_waitlist.append(
                {
                    "id": str(uuid4()),
                    "email": email,
                    "name": body.name,
                    "source": body.source,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            logger.info("Waitlist signup (memory): %s (source: %s)", email, body.source)
            return WaitlistResponse(
                message="Thanks! We'll notify you when Pro launches."
            )

        existing = (
            client.table("waitlist").select("id").eq("email", email).execute()
        )
        if existing.data:
            return WaitlistResponse(
                message="You're already on the waitlist! We'll reach out soon.",
                already_joined=True,
            )

        client.table("waitlist").insert(
            {
                "email": email,
                "name": body.name,
                "source": body.source,
            }
        ).execute()

        logger.info("Waitlist signup: %s (source: %s)", email, body.source)
        return WaitlistResponse(message="Thanks! We'll notify you when Pro launches.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Waitlist signup failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to join waitlist. Please try again.",
        ) from e
