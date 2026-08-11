"""Waitlist route — collect Pro tier interest. No auth required."""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr, field_validator

from app.config import settings
from app.rate_limit import limiter

logger = logging.getLogger("api")

router = APIRouter(prefix="/api/waitlist", tags=["waitlist"])

_memory_waitlist: list[dict[str, Any]] = []

# Attribution for Pro interest — keep in sync with frontend waitlist-source.ts
ALLOWED_WAITLIST_SOURCES = frozenset(
    {
        "normal",
        "pages_exhausted",
        "inbound_email",
        "pricing_page",  # legacy → normalized to normal
    }
)


def normalize_waitlist_source(raw: str | None) -> str:
    value = (raw or "normal").strip().lower() or "normal"
    if value == "pricing_page":
        return "normal"
    if value not in ALLOWED_WAITLIST_SOURCES:
        return "normal"
    return value


def reset_memory_waitlist() -> None:
    """Clear in-memory waitlist (tests only)."""
    _memory_waitlist.clear()


class WaitlistRequest(BaseModel):
    email: EmailStr
    name: str = ""
    source: str = "normal"

    @field_validator("source", mode="before")
    @classmethod
    def _normalize_source(cls, value: Any) -> str:
        return normalize_waitlist_source(str(value) if value is not None else None)


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
@limiter.limit(lambda: settings.rate_limit_waitlist)
async def join_waitlist(
    request: Request,
    payload: WaitlistRequest,
) -> WaitlistResponse:
    """Add an email to the Pro waitlist. No authentication required."""
    email = str(payload.email).strip().lower()
    try:
        client = _supabase_client()

        if client is None:
            for entry in _memory_waitlist:
                if entry.get("email") == email:
                    prior = entry.get("source") or "normal"
                    if prior != payload.source:
                        logger.info(
                            "Waitlist re-interest (memory): %s prior=%s new=%s",
                            email,
                            prior,
                            payload.source,
                        )
                    return WaitlistResponse(
                        message="You're already on the waitlist! We'll reach out soon.",
                        already_joined=True,
                    )
            _memory_waitlist.append(
                {
                    "id": str(uuid4()),
                    "email": email,
                    "name": payload.name,
                    "source": payload.source,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            logger.info("Waitlist signup (memory): %s (source: %s)", email, payload.source)
            return WaitlistResponse(
                message="Thanks! We'll notify you when Pro launches."
            )

        existing = (
            client.table("waitlist")
            .select("id, source")
            .eq("email", email)
            .execute()
        )
        if existing.data:
            prior = existing.data[0].get("source") or "normal"
            if prior != payload.source:
                logger.info(
                    "Waitlist re-interest: %s prior=%s new=%s",
                    email,
                    prior,
                    payload.source,
                )
            return WaitlistResponse(
                message="You're already on the waitlist! We'll reach out soon.",
                already_joined=True,
            )

        client.table("waitlist").insert(
            {
                "email": email,
                "name": payload.name,
                "source": payload.source,
            }
        ).execute()

        logger.info("Waitlist signup: %s (source: %s)", email, payload.source)
        return WaitlistResponse(message="Thanks! We'll notify you when Pro launches.")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Waitlist signup failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Failed to join waitlist. Please try again.",
        ) from e
