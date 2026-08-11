# Backend Launch — LLM Switch + JWT Auth + Budget Protection + Waitlist + Extraction Upgrades

> Transcribed from `backend-launch-prompt/` screenshots (Aug 9, 2026).


> **What this is:** One-shot Cursor prompt. Switch extraction to GPT-4o, add JWT auth, page metering, budget protection, waitlist, analytics, fix refine preview
targeting, add RapidOCR, layout-preserving text, confidence scores, validation, and targeted re-extraction. All changes in `backend/`. ~22 hours total.
>
> **How to use:** Paste from START to END into Cursor.
---

## --- START PROMPT ---

You are adding authentication, LLM model routing, usage metering, and budget protection to the AgentFlow backend. Codebase: `github.com/kabirrao2002/agentflow`, branch
  `develop`, working in `backend/`.
### What this covers (22 tasks):
### What this covers (22 tasks):
1. Add OpenAI + JWT + OCR + layout settings to `config.py`
2. Create OpenAI client with native `json_schema` mode + logprobs
3. Create LLM router (picks OpenAI vs Groq per task)
4. Wire extraction to use router instead of `groq_client` directly
5. Create JWT token utilities (create + validate)
6. Update auth route to return JWT token
7. Add `get_current_user` auth dependency - protect all routes
8. Apply auth dependency to ALL protected route files
9. Switch rate limiting to per-user for authenticated routes
10. Supabase migration - new tables (usage_events, waitlist, analytics_events, is_admin)
11. Create usage metering service
12. Enforce hard cap + refine limit in run routes
13. Add usage API endpoint
14. Create waitlist endpoint
15. Add analytics event logging service
16. Fix refine preview - untargeted field corrections
    18. Next.js UI updates for extraction progress
18. Add logprobs + per-field confidence scoring
19. Add RapidOCR as alternative OCR engine
20. Add layout-preserving text via Docling
22. Targeted field re-extraction in refine
22. Targeted field re-extraction in refine
### Critical rules:
- Do NOT modify `groq_client.py` - keep as-is. Add `openai_client.py` alongside it.
- Router pattern: extraction code calls `router.py`, which picks the right LLM. Extraction code never imports a specific client directly.
- Public routes (NO auth): `/api/auth/session`, `/api/health`, `/api/waitlist`
- Protected routes (auth REQUIRED): everything else
- Hard cap = 429 HTTP status. Global cap = 503.
- JWT secret: generate via `python -c "import secrets; print(secrets.token_urlsafe(32))"`, store as `JWT_SECRET_KEY` in `.env`
- Install new deps: `openai`, `python-jose[cryptography]`, `rapidocr-onnxruntime`, `docling`
- OCR engine is config-driven via `OCR_ENGINE` env var. Keep Tesseract as default fallback.
- Confidence scores use OpenAI logprobs - return per-field confidence (0.0-1.0) alongside extracted values

---

### TASK 1: Add OpenAI + JWT settings to config

**File:** `app/config.py`

Add these fields to the `Settings` class, AFTER the existing Groq settings:

```python
    # OpenAI - primary extraction model
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    # Comma-separated OpenAI fallbacks (Mini as fallback for cost savings)
    openai_fallback_models: str = "gpt-4o-mini"

    # JWT authentication
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 72

    # Usage limits
    free_page_limit_monthly: int = 50
    max_refines_per_run: int = 10
    global_daily_page_limit: int = 500

    # OCR engine - "tesseract" or "rapidocr"
    ocr_engine: str = "rapidocr"

    # Layout preservation - use Docling for digital PDFs
    use_layout_preservation: bool = True
```

Add this property to the `Settings` class:

```python
    @property
    def openai_fallback_models_list(self) -> list[str]:
        return [
            model.strip()
            for model in self.openai_fallback_models.split(",")
            if model.strip()
        ]
```

---

### TASK 2: Create OpenAI client with `json_schema` mode

**New file:** `app/services/llm/openai_client.py`

Create this file with the ENTIRE content:

```python
"""
OpenAI LLM client - structured extraction with native JSON Schema mode.

Uses response_format type=json_schema for constrained output.
This guarantees valid JSON matching the provided schema - zero format errors.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

from openai import AsyncOpenAI, APIConnectionError, APIStatusError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger("llm")

_client: Optional[AsyncOpenAI] = None


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, APIConnectionError):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in (500, 502, 503, 504, 429)
    return False


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to backend/.env"
            )
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_retryable),
)
async def _create_completion(
    client: AsyncOpenAI,
    *,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
    json_schema: Optional[dict[str, Any]] = None,
):
    response_format: dict[str, Any]
    if json_schema:
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "extraction_result",
                "strict": True,
                "schema": json_schema,
            },
        }
    else:
        response_format = {"type": "json_object"}

    return await client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=response_format,
        temperature=0,
        logprobs=True,
        top_logprobs=5,
    )


@dataclass
class LLMResult:
    """Result from an LLM call, including parsed JSON and token logprobs."""
    parsed: dict[str, Any]
    logprobs: list[Any] | None = None  # Token-level logprobs for confidence scoring


async def complete_json(
    system_prompt: str,
    user_prompt: str,
    *,
    model: Optional[str] = None,
    json_schema: Optional[dict[str, Any]] = None,
    return_logprobs: bool = False,
) -> dict[str, Any] | LLMResult:
    """
    Call OpenAI and parse the response as JSON.

    If json_schema is provided, uses response_format type=json_schema
    for constrained output (guaranteed valid). Otherwise falls back to
    json_object mode.

    If return_logprobs=True, returns LLMResult with both parsed JSON and
    token logprobs (for confidence scoring). Otherwise returns dict.
    """
    client = _get_client()
    primary = model or settings.openai_model
    candidates = [primary]
    for name in settings.openai_fallback_models_list:
        if name and name not in candidates:
            candidates.append(name)

    last_exc: BaseException | None = None

    for index, model_name in enumerate(candidates):
        logger.info(
            "OpenAI request — model=%s%s",
            model_name,
            "(primary)" if index == 0 else " (fallback)",
        )
        try:
            response = await _create_completion(
                client,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_schema=json_schema,
            )
            raw = response.choices[0].message.content or "{}"
            try:
                parsed = json.loads(raw)
                if return_logprobs:
                    token_logprobs = None
                    if response.choices[0].logprobs and response.choices[0].logprobs.content:
                        token_logprobs = response.choices[0].logprobs.content
                    return LLMResult(parsed=parsed, logprobs=token_logprobs)
                return parsed
            except json.JSONDecodeError as e:
                last_exc = RuntimeError("LLM returned invalid JSON")
            last_exc.__cause__ = e
            logger.error(
                "OpenAI model=%s returned invalid JSON: %s",
                model_name,
                raw[:500],
            )
        except BaseException as exc:
            last_exc = exc

        if index < len(candidates) - 1:
            logger.warning(
                "OpenAI failed on model=%s (%s) - trying fallback model=%s",
                model_name,
                last_exc,
                candidates[index + 1],
            )
            continue

        break

    assert last_exc is not None
    raise last_exc
---

---

### TASK 3: Create LLM router

**New file:** `app/services/llm/router.py`

Create this file with the ENTIRE content:

```python
"""
LLM Router - picks the right LLM client based on task type.

Extraction -> OpenAI GPT-4o Mini (json_schema mode, highest accuracy)
Plan Mode -> Groq Llama 3.1 8B (cheap, fast clarification)
Refiner -> Groq Llama 3.3 70B (complex prompt editing)
Planner -> Groq (pipeline planning)
"""

import logging
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("llm")


class LLMTask(str, Enum):
    EXTRACTION = "extraction"
    PLAN_MODE = "plan_mode"
    REFINER = "refiner"
    PLANNER = "planner"


async def complete_json(
    system_prompt: str,
    user_prompt: str,
    *,
    task: LLMTask = LLMTask.EXTRACTION,
    model: Optional[str] = None,
    json_schema: Optional[dict[str, Any]] = None,
    return_logprobs: bool = False,
) -> dict[str, Any]:
    """
    Route an LLM call to the appropriate provider based on task type.

    - EXTRACTION -> OpenAI (json_schema mode for guaranteed structure)
    - PLAN_MODE, REFINER, PLANNER -> Groq (fast, cheap)
    """
    if task == LLMTask.EXTRACTION:
        from app.services.llm.openai_client import complete_json as openai_complete
        logger.info("Router: task=%s -> OpenAI", task.value)
        return await openai_complete(
            system_prompt,
            user_prompt,
            model=model,
            json_schema=json_schema,
            return_logprobs=return_logprobs,
        )
    else:
        from app.services.llm.groq_client import complete_json as groq_complete
        logger.info("Router: task=%s -> Groq", task.value)
        return await groq_complete(
            system_prompt,
            user_prompt,
            model=model,
        )
    ...


---
### TASK 4: Wire extraction to use router

**File:** `app/services/extraction/field_extractor.py`

Find this import:

```python
from app.services.llm.groq_client import complete_json
```

REPLACE with:

```python
from app.services.llm.router import LLMTask, complete_json
```

Then find the call inside `extract_fields()`:

```python
    parsed = await complete_json(SYSTEM_PROMPT, user_prompt)
```

REPLACE with:

```python
    parsed = await complete_json(SYSTEM_PROMPT, user_prompt, task=LLMTask.EXTRACTION)
```

**IMPORTANT:** Do NOT change `groq_client.py`. Other code that imports from it directly (refine_chat, planner, etc.) keeps working as-is.

---

### TASK 5: Create JWT token utilities

**New file:** `app/services/auth/jwt.py`

Create this file with the ENTIRE content:

```python
"""
JWT token creation and validation.

Tokens contain user_id, email, and expiry. Used by the auth dependency
to identify the current user on every protected request.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger("auth")


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid, expired, or malformed."""
    pass


def create_access_token(
    user_id: str,
    email: str,
    *,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    if not settings.jwt_secret_key:
        raise RuntimeError(
            "JWT_SECRET_KEY is not set. Generate one with: "
            "'python -c import secrets; print(secrets.token_urlsafe(32))'"
        )

    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(hours=settings.jwt_expiry_hours))

    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT token. Returns the payload dict.

    Raises InvalidTokenError if the token is expired, malformed, or invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError("Token missing user_id (sub)")
        return payload
    except JWTError as e:
        logger.warning("JWT decode failed: %s", e)
        raise InvalidTokenError(f"Invalid token: {e}") from e


---

### TASK 6: Update auth route to return JWT token

**File:** `app/api/routes/auth.py`

REPLACE the ENTIRE file content with:

```python
"""Auth routes - sign in / register via configured auth provider. Returns JWT."""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import AuthServiceDep
from app.models.api.auth import SignInRequest, SignInResponse
from app.models.api.users import UserResponse
from app.services.auth.jwt import create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_user_response(user) -> UserResponse:
    return UserResponse(
        user_id=user.user_id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )


@router.post("/session", response_model=SignInResponse)
async def create_session(body: SignInRequest, auth: AuthServiceDep) -> SignInResponse:
    """
    Sign in or create an account. Returns user + JWT token.
    """
    Users are matched by email in the database (Supabase when configured).
    Same email always returns the same user_id and workflows.
    try:
        user, is_new = auth.sign_in_or_register(body.name, body.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    token = create_access_token(user.user_id, user.email)

    return SignInResponse(
        user=_to_user_response(user),
        is_new_user=is_new,
        auth_provider=auth.provider_name,
        token=token,
    )
...


**File:** `app/models/api/auth.py`

Find the `SignInResponse` model and ADD the `token` field:

```python
    token: str
```

If the model looks like this:

```python
class SignInResponse(BaseModel):
    user: UserResponse
    is_new_user: bool
    auth_provider: str
```

Change it to:

```python
class SignInResponse(BaseModel):
    user: UserResponse
    is_new_user: bool
    auth_provider: str
    token: str
```

---

### TASK 7: Add `get_current_user` auth dependency

**File:** `app/api/dependencies.py`

Add these imports at the top:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.services.auth.jwt import InvalidTokenError, decode_access_token
```

Add the security scheme and dependency function BEFORE the existing dependency functions:

```python
_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    repo: DataRepository = Depends(get_repo),
) -> "UserResponse":
    """
    Extract and validate JWT from Authorization header.
    Returns the authenticated user. Raises 401 if missing/invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    from app.services.users.user_service import UserService, UserNotFoundError
    user_service = UserService(repo)
    try:
        user = user_service.fetch_user(user_id)
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please sign in again.",
        )

        from app.models.api.users import UserResponse
        return UserResponse(
            user_id=user.user_id,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
        )
---

Add the type alias at the bottom with the other aliases:

```python
from app.models.api.users import UserResponse as UserResponseModel
CurrentUserDep = Annotated[UserResponseModel, Depends(get_current_user)]
```

Add "CurrentUserDep" and "get_current_user" to the `__all__` list.

---

### TASK 8: Apply auth dependency to ALL protected routes

For EACH of these route files, add `CurrentUserDep` as a parameter to every endpoint function (except the ones listed as public):

**Public (NO auth):** `auth.py`, `health.py`, `waitlist.py` (new)

**Protected (ADD `current_user: CurrentUserDep` parameter):**

**File:** `app/api/routes/runs.py`
  - Add `from app.api.dependencies import CurrentUserDep` (if not already imported)
  - Add `current_user: CurrentUserDep` parameter to: `run_adhoc`, `run_template`, `run_pipeline_steps`, `refine_plan`, `refine_run`, `get_run_status` 

**File:** `app/api/routes/users.py`
  - Add `current_user: CurrentUserDep` parameter to: `list_all_users`, `get_user`, `list_user_workflows` 
  - Keep `register_user` as-is (it's called during signup flow)

**File:** `app/api/routes/upload.py`
  - Add `current_user: CurrentUserDep` parameter to ALL endpoints

**File:** `app/api/routes/uploads.py`
  - Add `current_user: CurrentUserDep` parameter to ALL endpoints

**File:** `app/api/routes/workflows.py`
  - Add `current_user: CurrentUserDep` parameter to ALL endpoints

**File:** `app/api/routes/templates.py`
  - Add `current_user: CurrentUserDep` parameter to ALL endpoints

**File:** `app/api/routes/template_versions.py`
  - Add `current_user: CurrentUserDep` parameter to ALL endpoints

**File:** `app/api/routes/email.py`
  - Add `current_user: CurrentUserDep` parameter to ALL endpoints

**File:** `app/api/routes/sheets.py`
  - Add `current_user: CurrentUserDep` parameter to ALL endpoints

**File:** `app/api/routes/extract.py`
  - Add `current_user: CurrentUserDep` parameter to ALL endpoints

**File:** `app/api/routes/inbound.py`
  - This is a webhook - keep as-is (authenticated via `inbound_webhook_secret`)

**File:** `app/api/routes/inbound_addresses.py`
  - Add `current_user: CurrentUserDep` parameter to ALL endpoints

**File:** `app/api/routes/admin.py`
  - Keep existing admin_api_key auth - no change needed

Pattern for each endpoint - add the parameter, that's it. FastAPI auto-validates the JWT via the dependency. Example:

```python
# BEFORE
@router.post("/adhoc", response_model=RunResponse)
@limiter.limit(settings.rate_limit_runs_adhoc)
async def run_adhoc(
    request: Request,
    body: RunAdhocRequest,
    background_tasks: BackgroundTasks,
) -> RunResponse:
# AFTER
@router.post("/adhoc", response_model=RunResponse)
@limiter.limit(settings.rate_limit_runs_adhoc)
async def run_adhoc(
    request: Request,
    body: RunAdhocRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUserDep,
) -> RunResponse:
---


---

### TASK 9: Switch rate limiting to per-user

**File:** `app/rate_limit.py`

REPLACE the ENTIRE file content with:

```python
"""Shared rate limiter - per-user for authenticated routes, per-IP for public."""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_rate_limit_key(request: Request) -> str:
    """Use user_id from JWT if available, otherwise fall back to IP."""
    # The auth dependency stores user info in request.state if available
    user = getattr(request.state, "current_user", None)
    if user and hasattr(user, "user_id"):
        return f"user:{user.user_id}"
    return get_remote_address(request)


limiter = Limiter(key_func=_get_rate_limit_key)
```



### TASK 10: Supabase migration - new tables

**New file:** `supabase/migrations/005_launch_tables.sql`

Create this file with the ENTIRE content:

```sql
-- Launch tables: usage tracking, waitlist, analytics, admin flag

-- Usage events - track page extractions per user
CREATE TABLE IF NOT EXISTS usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pages INT NOT NULL DEFAULT 1,
    template_id TEXT,
    run_id UUID REFERENCES workflow_runs(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL DEFAULT 'extraction',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_usage_events_user_month
    ON usage_events(user_id, created_at);

-- Waitlist - collect Pro tier interest
CREATE TABLE IF NOT EXISTS waitlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'pricing_page',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_waitlist_email
    ON waitlist(email);

-- Analytics events - track product usage
CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    template_id TEXT,
    run_id UUID REFERENCES workflow_runs(id) ON DELETE SET NULL,
    duration_ms INT,
    page_count INT,
    error TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_analytics_events_type_date
    ON analytics_events(event_type, created_at);

-- Add admin flag to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false;

---

### TASK 11: Create usage metering service
**New file:** `app/services/usage/__init__.py`

Empty file.

**New file:** `app/services/usage/metering.py`

Create this file with the ENTIRE content:

```python
"""
Usage metering - track and enforce page extraction limits.

Free tier: 50 pages/month per user.
Global daily cap: 500 pages/day across all users (budget protection).
Refine limit: 10 refinements per run.
"""

import logging
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger("usage")


class UsageLimitError(Exception):
    """Raised when a user exceeds their page limit."""
    pass


class GlobalCapError(Exception):
    """Raised when the global daily page cap is hit."""
    pass


class RefineLimitError(Exception):
    """Raised when a run exceeds its refine limit."""
    pass


async def get_user_usage_this_month(supabase_client, user_id: str) -> int:
async def get_user_usage_this_month(supabase_client, user_id: str) -> int:
    """Count pages used by this user in the current calendar month."""
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = supabase_client.table("usage_events").select(
    result = supabase_client.table("usage_events").select(
        "pages", count="exact"
        "user_id", user_id
        "user_id", user_id
        "created_at", month_start.isoformat()
        "created_at", month_start.isoformat()
    ).execute()
    total = sum(row["pages"] for row in (result.data or []))
    total = sum(row["pages"] for row in (result.data or []))
    return total

async def get_global_usage_today(supabase_client) -> int:
async def get_global_usage_today(supabase_client) -> int:
    """Count total pages extracted today across all users."""
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    result = supabase_client.table("usage_events").select(
        "pages", count="exact"
    ).gte(
        "created_at", day_start.isoformat()
    ).execute()

    total = sum(row["pages"] for row in (result.data or []))
    return total


async def get_run_refine_count(supabase_client, run_id: str) -> int:
    """Count how many refinements have been done on this run (child runs)."""
    result = supabase_client.table("workflow_runs").select(
        "id", count="exact"
    ).eq(
        "parent_run_id", run_id
    ).execute()

    return len(result.data or [])


async def check_usage_allowed(
    supabase_client,
    user_id: str,
    page_count: int = 1,
) -> None:
    """
    Check all usage limits before allowing an extraction.
    Raises UsageLimitError or GlobalCapError if limits exceeded.
    """
    # Check global daily cap first (protects budget)
    daily_total = await get_global_usage_today(supabase_client)
    if daily_total + page_count > settings.global_daily_page_limit:
        logger.warning(
            "Global daily cap hit: %d + %d > %d",
            daily_total, page_count, settings.global_daily_page_limit,
        )
        raise GlobalCapError(
            "Service is temporarily at capacity. Please try again later."
        )

        # Check per-user monthly limit
        user_total = await get_user_usage_this_month(supabase_client, user_id)
        if user_total + page_count > settings.free_page_limit_monthly:
            logger.info(
                "User %s hit monthly limit: %d + %d > %d",
                user_id, user_total, page_count, settings.free_page_limit_monthly,
            )
            raise UsageLimitError(
                f"You've used {user_total} of your {settings.free_page_limit_monthly} "
                f"free pages this month. Join the Pro waitlist for unlimited access."
            )


async def check_refine_allowed(supabase_client, run_id: str) -> None:
    """Check if this run can be refined further."""
    count = await get_run_refine_count(supabase_client, run_id)
    if count >= settings.max_refines_per_run:
        raise RefineLimitError(
            f"This run has reached the maximum of {settings.max_refines_per_run} "
            f"refinements. Start a new extraction to continue."
        )


async def record_usage(
    supabase_client,
    user_id: str,
    pages: int,
    *,
    template_id: str | None = None,
    run_id: str | None = None,
    event_type: str = "extraction",
) -> None:
    """Record a usage event."""
    supabase_client.table("usage_events").insert({
        "user_id": user_id,
        "pages": pages,
        "template_id": template_id,
        "run_id": run_id,
        "event_type": event_type,
    }).execute()

    logger.info(
        "Usage recorded: user=%s pages=%d type=%s run=%s",
        user_id, pages, event_type, run_id,
    )


async def get_usage_summary(supabase_client, user_id: str) -> dict:
    """Get usage summary for the API response."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Next month start for reset date
    if now.month == 12:
        next_month = month_start.replace(year=now.year + 1, month=1)
    else:
        next_month = month_start.replace(month=now.month + 1)

    pages_used = await get_user_usage_this_month(supabase_client, user_id)

    return {
        "pages_used": pages_used,
        "pages_limit": settings.free_page_limit_monthly,
        "resets_at": next_month.isoformat(),
    }
```

---

### TASK 12: Enforce hard cap + refine limit in run routes

**File:** `app/api/routes/runs.py`

Add these imports at the top:

```python
from app.api.dependencies import CurrentUserDep
from app.services.usage.metering import (
    UsageLimitError,
    GlobalCapError,
    RefineLimitError,
    check_usage_allowed,
    check_refine_allowed,
    record_usage,
)


In `run_adhoc` function, BEFORE `plan = await create_plan(...)`, add usage check:

```python
    # --- Usage check ---
    try:
        from app.persistence import get_repository
        repo_inst = get_repository()
        supabase = getattr(repo_inst, '_client', None)
        if supabase:
            doc_count = 1  # Will be updated after upload loads
            await check_usage_allowed(supabase, current_user.user_id, doc_count)
    except UsageLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except GlobalCapError as e:
        raise HTTPException(status_code=503, detail=str(e))
    ...

After `_schedule_run(background_tasks, run.run_id)`, add recording:

```python
    # Record usage
    try:
        if supabase:
            page_count = len(run.document_ids) if hasattr(run, 'document_ids') else 1
            await record_usage(
                supabase,
                current_user.user_id,
                page_count,
                run_id=run.run_id,
            )
    except Exception as e:
        logger.warning("Failed to record usage: %s", e)
```

Apply the SAME pattern to `run_template`.

In `refine_run` function, BEFORE `run, summary = await refine_service.refine_and_start(...)`, add refine limit check:

```python
    # --- Refine limit check ---
    try:
        from app.persistence import get_repository
        repo_inst = get_repository()
        supabase = getattr(repo_inst, '_client', None)
        if supabase:
            await check_refine_allowed(supabase, run_id)
    except RefineLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
```

---

### TASK 13: Add usage API endpoint

**File:** `app/api/routes/users.py`

Add this import:

```python
from app.api.dependencies import CurrentUserDep
from app.services.usage.metering import get_usage_summary
```

Add this endpoint:

```python
@router.get("/me/usage")
async def get_my_usage(current_user: CurrentUserDep) -> dict:
    """Get the authenticated user's usage stats for the current month."""
    try:
        from app.persistence import get_repository
        repo = get_repository()
        supabase = getattr(repo, '_client', None)
        if supabase:
            return await get_usage_summary(supabase, current_user.user_id)
        return {
            "pages_used": 0,
            "pages_limit": 50,
            "resets_at": None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch usage: {e}")
```

**IMPORTANT:** Place this route BEFORE the `/{user_id}` route so FastAPI doesn't interpret "me" as a user_id.

---

### TASK 14: Create waitlist endpoint

**New file:** `app/api/routes/waitlist.py`

Create this file with the ENTIRE content:

```python
"""Waitlist route - collect Pro tier interest. No auth required."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

logger = logging.getLogger("api")

router = APIRouter(prefix="/api/waitlist", tags=["waitlist"])


class WaitlistRequest(BaseModel):
    email: EmailStr
    name: str = ""
    source: str = "pricing_page"


class WaitlistResponse(BaseModel):
    message: str
    already_joined: bool = False


@router.post("", response_model=WaitlistResponse)
async def join_waitlist(body: WaitlistRequest) -> WaitlistResponse:
    """Add an email to the Pro waitlist. No authentication required."""
    try:
        from app.persistence import get_repository
        repo = get_repository()
        supabase = getattr(repo, '_client', None)

        if not supabase:
            logger.info("Waitlist signup (no DB): %s", body.email)
            return WaitlistResponse(message="Thanks! We'll notify you when Pro launches.")

        # Check if already on waitlist
        existing = supabase.table("waitlist").select("id").eq(
            "email", body.email
        ).execute()

        if existing.data:
            return WaitlistResponse(
                message="You're already on the waitlist! We'll reach out soon.",
                already_joined=True,
            )

        supabase.table("waitlist").insert({
            "email": body.email,
            "name": body.name,
            "source": body.source,
        }).execute()

        logger.info("Waitlist signup: %s (source: %s)", body.email, body.source)
        return WaitlistResponse(message="Thanks! We'll notify you when Pro launches.")

    except Exception as e:
        logger.error("Waitlist signup failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to join waitlist. Please try again.")
```

**File:** `app/main.py`

Add the import and router registration:

```python
from app.api.routes import waitlist
# ...
app.include_router(waitlist.router)
```

---

### TASK 15: Add analytics event logging service

**New file:** `app/services/analytics/__init__.py`

Empty file.

**New file:** `app/services/analytics/events.py`

Create this file with the ENTIRE content:

```python
"""
Analytics event logging - track product usage for insights.

Events are written to Supabase analytics_events table.
Query via Supabase dashboard - no admin UI needed at launch.
"""

import logging
import time
from contextlib import contextmanager
from typing import Any, Optional

logger = logging.getLogger("analytics")


@contextmanager
def track_duration():
    """Context manager that yields a callable to get elapsed ms."""
    start = time.monotonic()
    result = {"ms": 0}
    try:
        yield result
    finally:
        result["ms"] = int((time.monotonic() - start) * 1000)


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
    """Log an analytics event to Supabase. Fails silently."""
    try:
        from app.persistence import get_repository
        repo = get_repository()
        supabase = getattr(repo, '_client', None)

        if not supabase:
            logger.debug("Analytics skip (no DB): %s", event_type)
            return


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

        supabase.table("analytics_events").insert(row).execute()

        logger.warning("Analytics log failed: %s (event=%s)", e, event_type)


---

### TASK 16: Fix refine preview - untargeted field corrections

**File:** `app/services/pipeline/refine_preview.py`

Find the `_infer_target_fields` function and REPLACE it with:

```python
def _infer_target_fields(
    accumulated_instruction: str,
    planned_changes: list[str],
    all_fields: list[str],
) -> set[str]:
    """Match field names from instruction/changes, handling underscores and spaces."""
    haystack = " ".join([accumulated_instruction, *planned_changes]).lower()
    matched: set[str] = set()

    for field in all_fields:
        field_lower = field.lower()
        # Direct match
        if field_lower in haystack:
            matched.add(field)
            continue
        # Underscore -> space match (e.g. "vendor_name" matches "vendor name")
        field_spaced = field_lower.replace("_", " ")
        if field_spaced in haystack:
            matched.add(field)
            continue

        # Space -> underscore match
        field_underscored = field_lower.replace(" ", "_")
        if field_underscored in haystack:
            matched.add(field)
            continue

        # Partial word match (e.g. "vendor" in "fix vendor")
        for word in field_lower.replace("_", " ").split():
            if len(word) >= 4 and word in haystack:
                matched.add(field)
                break

    return matched


Then find the preview diff loop. In the section where `field_previews` are built, find this line:

```python
    candidates = target_fields or set(fields)
```

REPLACE the entire candidates/filtering block with a stricter version:

```python
    # Only show diffs for targeted fields. If no targets matched,
            # skip field-level preview entirely (show planned_changes text only).
            if not target_fields:
                logger.info(
                    "[refine] preview: no target fields matched, skipping field-level diff run_id=%s",
                    run.run_id,
                )
                continue

            candidates = target_fields
...

Also add value normalization BEFORE comparison. Find:

```python
                before = _format_value(before_row.get(field))
                after = _format_value(after_fields.get(field))
                if before == after and field not in target_fields:
                    continue
```

REPLACE with:

```python
                before = _format_value(before_row.get(field))
                after = _format_value(after_fields.get(field))
                # Normalize for comparison to avoid false diffs from LLM non-determinism
                if _values_equivalent(before, after):
                    continue
```

Add this helper function above `preview_refinement`:

```python
def _values_equivalent(a: Any, b: Any) -> bool:
    """Compare values with normalization to avoid false diffs."""
    if a == b:
        return True
    if a is None or b is None:
        return False
    # String normalization: strip whitespace, case-insensitive
    if isinstance(a, str) and isinstance(b, str):
        return a.strip().lower() == b.strip().lower()
    # Numeric: compare with tolerance
    try:
        fa, fb = float(a), float(b)
        return abs(fa - fb) < 0.01
    except (ValueError, TypeError):
        pass
    return str(a).strip() == str(b).strip()
```



### TASK 17: Switch extraction model to GPT-4o

**Already handled in Task 1** -- the `openai_model` default is now `gpt-4o` instead of `gpt-4o-mini`. GPT-4o Mini is the fallback.

**Why:** GPT-4o gives 92.4% field accuracy vs ~75% for Mini. Cost difference at 50 docs/month is $0.60. Mini is a "structure destroyer" (13% structural fidelity) - even with `json_schema` mode, GPT-4o is significantly more reliable.
with `json_schema` mode, GPT-4o is significantly more reliable.
No additional code changes needed beyond Task 1.

---

### TASK 18: Add logprobs + per-field confidence scoring

**Already partially handled in Task 2** - `logprobs=True` and `top_logprobs=5` added to OpenAI client, `LLMResult` dataclass added with `return_logprobs` parameter.

**New file:** `app/services/extraction/confidence.py`

Create this file with the ENTIRE content:

```python
"""
Per-field confidence scoring using OpenAI token logprobs.

HOW IT WORKS:
1. OpenAI returns log-probabilities for each output token
2. We map tokens back to the JSON field values in the extraction output
3. For each field, we compute mean(exp(logprob)) across its value tokens
4. Result: confidence score 0.0-1.0 per extracted field

Based on Azure's open-source implementation:
github.com/azure/ai-document-processing-pipeline
"""

import json
import logging
import math
from typing import Any, Optional

logger = logging.getLogger("confidence")


def compute_field_confidence(
    parsed: dict[str, Any],
    logprobs: list[Any] | None,
    fields: list[str],
) -> dict[str, float]:
    """
    Compute per-field confidence scores from token logprobs.

    Returns: dict mapping field name -> confidence (0.0 to 1.0)
    """
    if not logprobs:
        logger.debug("No logprobs available - returning default confidence")
        return {field: 0.5 for field in fields}

    # Reconstruct the full output text from tokens
    tokens_with_probs: list[tuple[str, float]] = []
    for token_info in logprobs:
        token_text = token_info.token
        token_logprob = token_info.logprob
        tokens_with_probs.append((token_text, token_logprob))

    # Serialize the parsed output to find field value positions
    results = parsed.get("results", [])
    if not results:
        return {field: 0.5 for field in fields}

    field_confidences: dict[str, list[float]] = {field: [] for field in fields}

    # For each field, find the tokens that correspond to its value
    # by searching the token stream for the field's serialized value
    for result_item in results:
        result_fields = result_item.get("fields", {})
        for field in fields:
            value = result_fields.get(field)
            if value is None:
                # null values get neutral confidence
                field_confidences[field].append(0.5)
                continue

            # Serialize the value as it would appear in JSON
            value_str = json.dumps(value) if not isinstance(value, str) else value

            # Find matching tokens and collect their probabilities
            probs = _find_value_token_probs(tokens_with_probs, field, value_str)
            if probs:
                field_confidences[field].extend(probs)
            else:
                # Fallback: use overall average confidence
                all_probs = [math.exp(lp) for _, lp in tokens_with_probs if lp != 0.0]
                if all_probs:
                    field_confidences[field].append(sum(all_probs) / len(all_probs))
                else:
                    field_confidences[field].append(0.5)

    # Aggregate: mean probability per field
    result: dict[str, float] = {}
    for field in fields:
        probs = field_confidences[field]
        if probs:
            result[field] = round(sum(probs) / len(probs), 4)
        else:
            result[field] = 0.5

    return result


def _find_value_token_probs(
    tokens_with_probs: list[tuple[str, float]],
    field_name: str,
    value_str: str,
) -> list[float]:
    """
    Find tokens corresponding to a field's value in the token stream.

    Strategy: look for the field name token(s), then collect the value tokens
    that follow until the next field delimiter (comma, closing brace).
    """
    # Build the concatenated token text
    full_text = "".join(t for t, _ in tokens_with_probs)

    # Find the field name in the token stream
    field_pattern = f'"{field_name}"'
    field_pos = full_text.find(field_pattern)
    if field_pos == -1:
        # Try with underscore/space variants
        field_pattern_alt = f'"{field_name.replace("_", " ")}"'
        field_pos = full_text.find(field_pattern_alt)
        if field_pos == -1:
            return []

    # Find the value start (after the colon)
    colon_pos = full_text.find(":", field_pos + len(field_pattern))
    if colon_pos == -1:
        return []

    # Map character positions back to token indices
    char_pos = 0
    value_start_token_idx = None
    for idx, (token_text, _) in enumerate(tokens_with_probs):
        if char_pos >= colon_pos and value_start_token_idx is None:
            value_start_token_idx = idx
                break
            char_pos += len(token_text)

        if value_start_token_idx is None:
            return []

        # Collect probabilities for value tokens (skip whitespace/colon tokens)
        probs: list[float] = []
        depth = 0
        started = False
        for idx in range(value_start_token_idx, len(tokens_with_probs)):
            token_text, logprob = tokens_with_probs[idx]
            stripped = token_text.strip()

            if not started:
                if stripped in (":", ""):
                    continue
                started = True

            # Track nesting for arrays/objects
            for ch in stripped:
                if ch in ("{", "["):
                    depth += 1
                elif ch in ("}", "]"):
                    depth -= 1

        # End of value: comma at depth 0, or closing brace
        if depth < 0:
            break
        if depth == 0 and "," in stripped and not stripped.startswith('"'):
            break

        # Collect this token's probability
        prob = math.exp(logprob) if logprob != 0.0 else 1.0
        probs.append(prob)

    return probs


**File:** `app/services/extraction/field_extractor.py`

Update `extract_fields()` to use confidence scoring. Find:

```python
    user_prompt = _build_prompt(documents, fields, instructions)
    parsed = await complete_json(SYSTEM_PROMPT, user_prompt, task=LLMTask.EXTRACTION)

    return _parse_llm_response(parsed, documents, fields)
```

REPLACE with:

```python
    user_prompt = _build_prompt(documents, fields, instructions)
    result = await complete_json(
        SYSTEM_PROMPT, user_prompt,
        task=LLMTask.EXTRACTION,
        return_logprobs=True,
    )

    # Handle both LLMResult (with logprobs) and plain dict
    from app.services.llm.openai_client import LLMResult
    if isinstance(result, LLMResult):
        parsed = result.parsed
        from app.services.extraction.confidence import compute_field_confidence
        confidences = compute_field_confidence(parsed, result.logprobs, fields)
    else:
        parsed = result
        confidences = {field: 0.5 for field in fields}

    return _parse_llm_response(parsed, documents, fields, confidences)
...

Update `_parse_llm_response` to include confidence:

```python
def _parse_llm_response(
    parsed: dict[str, Any],
    documents: list[DocumentInput],
    fields: list[str],
    confidences: dict[str, float] | None = None,
) -> list[ExtractedDocument]:
    raw_results = parsed.get("results", [])
    by_id = {item.get("document_id"): item for item in raw_results}

    results: list[ExtractedDocument] = []
    for doc in documents:
        item = by_id.get(doc.document_id, {})
        field_values = item.get("fields", {}) if isinstance(item, dict) else {}

        normalized = {field: field_values.get(field) for field in fields}
        results.append(
            ExtractedDocument(
                document_id=doc.document_id,
                filename=doc.filename,
                fields=normalized,
                confidence=confidences or {},
            )
        )

    return results


Update `ExtractedDocument` dataclass:

```python
@dataclass
class ExtractedDocument:
    document_id: str
    filename: str
    fields: dict[str, Any]
    confidence: dict[str, float] = None  # Per-field confidence 0.0-1.0

    def __post_init__(self):
        if self.confidence is None:
            self.confidence = {}

---


### TASK 19: Add RapidOCR as alternative OCR engine

**New file:** `app/services/documents/ocr_engines.py`

Create this file with the ENTIRE content:

```python
"""
OCR engine abstraction - pluggable OCR backend.

Supports:
- tesseract: System Tesseract via pytesseract (default fallback)
- rapidocr: PaddleOCR models via ONNX Runtime (recommended, faster + more accurate)

Config: OCR_ENGINE env var or settings.ocr_engine
"""

import logging
import shutil
from pathlib import Path
from typing import Protocol

import numpy as np
from PIL import Image

from app.config import settings

logger = logging.getLogger("ocr")


class OCREngine(Protocol):
    """Interface for OCR engines."""
    def ocr_image(self, image: Image.Image) -> str: ...
    @property
    def name(self) -> str: ...


class TesseractEngine:
    """OCR using system Tesseract via pytesseract."""

    @property
    def name(self) -> str:
        return "tesseract"

    def ocr_image(self, image: Image.Image) -> str:
        import pytesseract
        if shutil.which("tesseract") is None:
            raise RuntimeError(
                "Tesseract is not installed. Install it with:\n"
                "  macOS:   brew install tesseract\n"
                "  Ubuntu:  sudo apt install tesseract-ocr\n"
                "  Windows: https://github.com/UB-Mannheim/tesseract/wiki"
            )
        return pytesseract.image_to_string(image)


class RapidOCREngine:
    """OCR using PaddleOCR models via ONNX Runtime, CPU-only, no GPU needed."""

    def __init__(self):
        try:
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()
        except ImportError:
            raise ImportError(
                "rapidocr-onnxruntime not installed. "
                "Install with: pip install rapidocr-onnxruntime"
            )

    @property
    def name(self) -> str:
        return "rapidocr"

    def ocr_image(self, image: Image.Image) -> str:
        # RapidOCR accepts numpy arrays
        img_array = np.array(image)
        result, _ = self._engine(img_array)
        if not result:
            return ""
        # result is list of [bbox, text, confidence]
        lines = [line[1] for line in result]
        return "\n".join(lines)


# Singleton engine instance
_engine: OCREngine | None = None


def get_ocr_engine() -> OCREngine:
    """Get the configured OCR engine (singleton)."""
    global _engine
    if _engine is None:
        engine_name = settings.ocr_engine.lower()
        if engine_name == "rapidocr":
            try:
                _engine = RapidOCREngine()
                logger.info("OCR engine: RapidOCR (ONNX)")
            except ImportError:
                logger.warning("RapidOCR not available, falling back to Tesseract")
                _engine = TesseractEngine()
        else:
            _engine = TesseractEngine()
            logger.info("OCR engine: Tesseract")
    return _engine
...

**File:** `app/services/documents/text_extractor.py`

Replace direct `pytesseract` usage with the OCR engine abstraction.

Find:

```python
import pytesseract
```

REPLACE with:

```python
from app.services.documents.ocr_engines import get_ocr_engine
```

Find the `_ocr_pdf` function's OCR call:

```python
    pages_text.append(pytesseract.image_to_string(img))
```

REPLACE with:

```python
    engine = get_ocr_engine()
    pages_text.append(engine.ocr_image(img))
```

Find `extract_text_from_image`'s OCR call:

```python
    text = pytesseract.image_to_string(img)
    return text.strip(), "tesseract"
```

REPLACE with:

```python
    engine = get_ocr_engine()
    text = engine.ocr_image(img)
    return text.strip(), engine.name
```

Remove the `_check_tesseract_installed()` function - it's now handled inside `TesseractEngine`.

Remove calls to `_check_tesseract_installed()` in `_ocr_pdf` and `extract_text_from_image`.

---

### TASK 20: Add layout-preserving text via Docling

**New file:** `app/services/documents/layout_extractor.py`

Create this file with the ENTIRE content:

```python
"""
Layout-preserving text extraction using Docling (IBM, open-source).

WHY: VAREX (CVPR 2026) showed that upgrading raw text to layout-preserving
text gives +3 to +18pp accuracy gain - more than switching to image input.
Docling converts PDFs to structured markdown with table detection.

WHEN TO USE:
- Digital PDFs (embedded text) -> Docling gives markdown with tables preserved
- Scanned PDFs -> Fall back to OCR (Docling needs embedded text layer)
- Images -> Fall back to OCR
"""

import logging
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger("layout")


def extract_layout_text(file_path: Path) -> Optional[str]:
    """
    Extract layout-preserving text from a PDF using Docling.
    
    Returns markdown string if successful, None if Docling is unavailable
    or the PDF is scanned (no embedded text).
    """
    if not settings.use_layout_preservation:
        return None
    
    if file_path.suffix.lower() != ".pdf":
        return None

    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(str(file_path))

        # Export as markdown - preserves tables, headers, structure
        markdown = result.document.export_to_markdown()

        if not markdown or len(markdown.strip()) < 50:
            logger.info("Docling produced sparse text for %s, falling back to OCR", file_path.name)
            return None

        logger.info(
            "Layout extraction: %s -> %d chars markdown",
            file_path.name,
            len(markdown),
        )
        return markdown.strip()

    except ImportError:
        logger.warning("Docling not installed - pip install docling")
        return None
    except Exception as e:
        logger.warning("Docling extraction failed for %s: %s", file_path.name, e)
        return None


**File:** `app/services/documents/text_extractor.py`

Update `extract_text_from_pdf` to try Docling first. Find the function:

```python
def extract_text_from_pdf(file_path: Path) -> tuple[str, str]:
    """
    Extract text from a PDF using PyMuPDF.

    Returns: (extracted_text, method_used)
    """
    doc = fitz.open(file_path)


Add Docling attempt BEFORE the PyMuPDF extraction:

```python
def extract_text_from_pdf(file_path: Path) -> tuple[str, str]:
    """
    Extract text from a PDF using layout-preserving extraction (Docling),
    falling back to PyMuPDF, then OCR.

    Returns: (extracted_text, method_used)
    """
    # Try layout-preserving extraction first (best accuracy)
    from app.services.documents.layout_extractor import extract_layout_text
    layout_text = extract_layout_text(file_path)
    if layout_text:
        return layout_text, "docling"

    doc = fitz.open(file_path)


---

### TASK 21: Post-extraction validation service

**New file:** `app/services/extraction/validators.py`

Create this file with the ENTIRE content:

```python
"""
Post-extraction validation - check extracted fields for common errors.

Runs AFTER extraction, BEFORE returning results to the user.
Does NOT re-extract - just flags suspicious values as warnings.

Validators:
- Date format check (should be YYYY-MM-DD)
- Amount sanity check (should be numeric, reasonable range)
- Required field presence (template-defined required fields should not be null)
- Line items total check (line items should sum to total amount)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("validation")

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
AMOUNT_MAX = 1_000_000_000  # $1B - anything above this is likely an error


@dataclass
class ValidationWarning:
    """A warning about a potentially incorrect extracted value."""
    field: str
    message: str
    severity: str = "warning"  # "warning" | "error"


@dataclass
class ValidationResult:
    """Result of validating extracted fields."""
    warnings: list[ValidationWarning] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def to_dict(self) -> list[dict[str, str]]:
        return [
            {"field": w.field, "message": w.message, "severity": w.severity}
            for w in self.warnings
        ]


def validate_extracted_fields(
    fields: dict[str, Any],
    *,
    date_fields: Optional[list[str]] = None,
    amount_fields: Optional[list[str]] = None,
    required_fields: Optional[list[str]] = None,
) -> ValidationResult:
    """
    Validate extracted field values and return warnings.

    Field type hints are inferred from field names if not explicitly provided:
    - Fields containing "date" -> date validation
    - Fields containing "amount", "total", "price", "cost", "tax" -> amount validation
    """
    result = ValidationResult()

    # Auto-detect field types from names if not provided
    if date_fields is None:
        date_fields = [f for f in fields if _is_date_field(f)]
    if amount_fields is None:
        amount_fields = [f for f in fields if _is_amount_field(f)]

    # Date validation
    for field_name in date_fields:
        value = fields.get(field_name)
        if value is None:
            continue
        if isinstance(value, str) and not DATE_PATTERN.match(value):
            result.warnings.append(ValidationWarning(
                field=field_name,
                message=f"Date not in YYYY-MM-DD format: '{value}'",
                severity="warning",
            ))

    # Amount validation
    for field_name in amount_fields:
        value = fields.get(field_name)
        if value is None:
            continue
        try:
            num = float(value) if isinstance(value, str) else float(value)
            if num < 0:
                result.warnings.append(ValidationWarning(
                    field=field_name,
                    message=f"Negative amount: {num}",
                    severity="warning",
                ))
            if abs(num) > AMOUNT_MAX:
                result.warnings.append(ValidationWarning(
                    field=field_name,
                    message=f"Unusually large amount: {num}",
                    severity="warning",
                ))
        except (ValueError, TypeError):
            result.warnings.append(ValidationWarning(
                field=field_name,
                message=f"Amount is not numeric: '{value}'",
                severity="error",
            ))

    # Required field presence
    if required_fields:
        for field_name in required_fields:
            value = fields.get(field_name)
            if value is None or (isinstance(value, str) and not value.strip()):
                result.warnings.append(ValidationWarning(
                    field=field_name,
                    message=f"Required field is empty",
                    severity="error",
                ))

        # Line items total check
        _check_line_items_total(fields, result)

        if result.has_warnings:
            logger.info(
                "Validation found %d warnings: %s",
                len(result.warnings),
                ", ".join(w.field for w in result.warnings),
            )

        return result


def _is_date_field(name: str) -> bool:
    """Heuristic: field name contains 'date'."""
    return "date" in name.lower()


def _is_amount_field(name: str) -> bool:
    """Heuristic: field name suggests a monetary amount."""
    lower = name.lower()
    return any(kw in lower for kw in ["amount", "total", "price", "cost", "tax", "subtotal", "fee"])


def _check_line_items_total(fields: dict[str, Any], result: ValidationResult) -> None:
    """Check if line items sum to the total amount (±1% tolerance)."""
    # Find total field
    total_value = None
    total_field = None
    for key in ("total_amount", "grand_total", "total", "amount_due", "net_amount"):
        if key in fields and fields[key] is not None:
            try:
                total_value = float(fields[key])
                total_field = key
                break
            except (ValueError, TypeError):
                pass

    if total_value is None:
        return

    # Find line items
    line_items = fields.get("line_items")
    if not isinstance(line_items, list) or not line_items:
        return

    # Sum line item amounts
    line_total = 0.0
    amount_keys = ("amount", "total", "line_total", "extended_price", "net_amount")
    for item in line_items:
        if not isinstance(item, dict):
            continue
        for key in amount_keys:
            if key in item and item[key] is not None:
                try:
                    line_total += float(item[key])
                    break
                except (ValueError, TypeError):
                    pass

        if line_total == 0:
            return

        # Check with tolerance
        tolerance = max(abs(total_value) * 0.02, 0.01) # 2% or $0.01
        diff = abs(total_value - line_total)
        if diff > tolerance:
            result.warnings.append(ValidationWarning(
                field=total_field,
                message=f"Line items sum ({line_total:.2f}) doesn't match total ({total_value:.2f})",
                severity="warning",
            ))
...

**File:** `app/services/extraction/field_extractor.py`

Add validation after extraction. In `extract_fields()`, after `_parse_llm_response(...)`, add:

```python
    # Post-extraction validation
    from app.services.extraction.validators import validate_extracted_fields
    for doc_result in extracted_docs:
        validation = validate_extracted_fields(doc_result.fields)
        doc_result.validation_warnings = validation.to_dict()
...

Update 'ExtractedDocument' to include validation:

```python
@dataclass
class ExtractedDocument:
    document_id: str
    filename: str
    fields: dict[str, Any]
    confidence: dict[str, float] = None
    validation_warnings: list[dict[str, str]] = None

    def __post_init__(self):
        if self.confidence is None:
            self.confidence = {}
        if self.validation_warnings is None:
            self.validation_warnings = []
...



### TASK 22: Targeted field re-extraction in refine

**File:** `app/services/extraction/field_extractor.py`

Add a new function for single-field re-extraction:

```python
async def extract_single_field(
    document: DocumentInput,
    field: str,
    instructions: Optional[str] = None,
) -> tuple[Any, float]:
    """
    Re-extract a single field from a document.
    Returns (value, confidence) - used by targeted refinement.
    Much cheaper than full re-extraction (~5x fewer tokens).
    """
    single_prompt = _build_prompt([document], [field], instructions)
    result = await complete_json(
        SYSTEM_PROMPT, single_prompt,
        task=LLMTask.EXTRACTION,
        return_logprobs=True,
    )

    from app.services.llm.openai_client import LLMResult
    if isinstance(result, LLMResult):
        parsed = result.parsed
        from app.services.extraction.confidence import compute_field_confidence
        conf = compute_field_confidence(parsed, result.logprobs, [field])
    else:
        parsed = result
        conf = {field: 0.5}

    # Extract the value from the response
    results = parsed.get("results", [])
    if results:
        value = results[0].get("fields", {}).get(field)
    else:
        value = None

        return value, conf.get(field, 0.5)


**File:** `app/services/pipeline/refine_service.py` (or wherever `refine_and_start` is defined)

When the refinement targets a single specific field (detected by `_infer_target_fields` returning exactly 1 field), use `extract_single_field` instead of full
re-extraction:

Add this check BEFORE starting the full re-extraction pipeline:

```python
    # Targeted re-extraction: if only one field is being refined,
    # re-extract just that field (5x cheaper, same accuracy)
    from app.services.pipeline.refine_preview import _infer_target_fields

    target_fields = _infer_target_fields(
        accumulated_instruction,
        planned_changes,
        list(all_fields),
    )

    if len(target_fields) == 1:
        target_field = list(target_fields)[0]
        logger.info(
            "[refine] targeted re-extraction for single field: %s",
            target_field,
    from app.services.extraction.field_extractor import extract_single_field, DocumentInput
    # Build document input from existing run data
    doc_input = DocumentInput(
        document_id=doc.document_id,
        text=doc.text,
        filename=doc.filename,
    )
    new_value, confidence = await extract_single_field(
        doc_input,
        target_field,
        instructions=accumulated_instruction,
    )

    # Update just this field in the existing results
    # (skip full pipeline re-run)
    # ... merge new_value into existing extracted fields

**Note:** The exact merge logic depends on how your refine service stores intermediate results. The pattern is: fetch existing extracted fields -> replace the target
field value -> save back -> return updated results. This avoids re-running OCR, planning, and extracting all other fields.
---

## File Change Summary

### New files (12):
| File | Purpose |
|---|---|
| `app/services/llm/openai_client.py` | OpenAI client with json_schema mode + logprobs |
| `app/services/llm/router.py` | LLM task router (OpenAI vs Groq) |
| `app/services/auth/jwt.py` | JWT token create + validate |
| `app/services/usage/__init__.py` | Package init |
| `app/services/usage/metering.py` | Usage tracking + limit enforcement |
| `app/services/analytics/__init__.py` | Package init |
| `app/services/analytics/events.py` | Analytics event logging |
| `app/api/routes/waitlist.py` | Waitlist signup endpoint |
| `app/services/extraction/confidence.py` | Per-field confidence scoring from logprobs |
| `app/services/documents/ocr_engines.py` | Pluggable OCR engine (Tesseract + RapidOCR) |
| `app/services/documents/layout_extractor.py` | Layout-preserving text via Docling |
| `app/services/extraction/validators.py` | Post-extraction field validation |
| `supabase/migrations/005_launch_tables.sql` | New DB tables |

### Modified files (16+):
| File | Change |
|---|---|
| `app/config.py` | Add OpenAI, JWT, usage limit, OCR engine, layout settings |
| `app/services/extraction/field_extractor.py` | Router import, confidence scoring, validation, single-field extraction |
| `app/api/routes/auth.py` | Return JWT token in response |
| `app/models/api/auth.py` | Add `token` field to SignInResponse |
| `app/api/dependencies.py` | Add `get_current_user` + `CurrentUserDep` |
| `app/api/routes/runs.py` | Add auth + usage checks |
| `app/api/routes/users.py` | Add auth + usage endpoint |
| `app/api/routes/upload.py` | Add auth |
| `app/api/routes/uploads.py` | Add auth |
| `app/api/routes/workflows.py` | Add auth |
| `app/api/routes/templates.py` | Add auth |
| `app/api/routes/template_versions.py` | Add auth |
| `app/api/routes/email.py` | Add auth |
| `app/api/routes/sheets.py` | Add auth |
| `app/api/routes/extract.py` | Add auth |
| `app/api/routes/inbound_addresses.py` | Add auth |
| `app/rate_limit.py` | Per-user rate limiting |
| `app/main.py` | Register waitlist router |
| `app/services/pipeline/refine_preview.py` | Fix target field matching + value normalization |
| `app/services/documents/text_extractor.py` | Use OCR engine abstraction + Docling layout extraction |
| `app/services/pipeline/refine_service.py` | Targeted single-field re-extraction |

### New dependencies:
Add to `requirements.txt`:
```
openai>=1.30.0
python-jose[cryptography]>=3.3.0
rapidocr-onnxruntime>=1.4.0
docling>=2.0.0
numpy>=1.24.0
```

### New environment variables (add to `.env`):

OPENAI_API_KEY=sk-...
JWT_SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(32))">
OCR_ENGINE=rapidocr
USE_LAYOUT_PRESERVATION=true


---

## Build order:
1. `pip install openai python-jose[cryptography] rapidocr-onnxruntime docling` + update requirements.txt
2. `config.py` - add all new settings (OpenAI, JWT, usage, OCR, layout)
3. `openai_client.py` - new file (with logprobs + LLMResult)
4. `router.py` - new file (with return_logprobs passthrough)
5. `field_extractor.py` - swap import, add confidence + validation + single-field extraction
6. `confidence.py` - new file
7. `validators.py` - new file
8. `ocr_engines.py` - new file
9. `layout_extractor.py` - new file
10. `text_extractor.py` - use OCR engine abstraction + Docling
11. `jwt.py` - new file
12. `auth.py` + `models/api/auth.py` - JWT token
13. `dependencies.py` - `get_current_user`
14. ALL route files - add `CurrentUserDep`
15. `rate_limit.py` - per-user keys
16. Run SQL migration in Supabase dashboard
17. `metering.py` - new file
18. `runs.py` - usage checks
19. `users.py` - usage endpoint
20. `waitlist.py` - new route + register in `main.py`
21. `events.py` - analytics
22. `refine_preview.py` - fix targeting
23. `refine_service.py` - targeted re-extraction

## --- END PROMPT ---

