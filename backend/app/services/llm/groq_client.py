"""
Groq LLM client — thin wrapper around the Groq API.

Groq exposes an OpenAI-compatible chat API. We use it for structured
JSON extraction from document text.

Primary models are configured per task in settings. On any failure from a
model (API error, invalid JSON, etc.) we fall through to configured fallbacks.
"""

import json
import logging
from typing import Any, Optional

from groq import APIConnectionError, APIStatusError, AsyncGroq
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.config import settings

logger = logging.getLogger("llm")

_client: Optional[AsyncGroq] = None


def _is_retryable_same_model(exc: BaseException) -> bool:
    """Retry transient failures on the same model before trying a fallback."""
    if isinstance(exc, APIConnectionError):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in (500, 502, 503, 504)
    return False


def _model_candidates(primary: str) -> list[str]:
    """Primary model first, then configured fallbacks (deduped, order preserved)."""
    candidates = [primary]
    for name in settings.groq_fallback_models_list:
        if name and name not in candidates:
            candidates.append(name)
    return candidates


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to backend/.env"
            )
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception(_is_retryable_same_model),
)
async def _create_completion(
    client: AsyncGroq,
    *,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
):
    return await client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )


async def complete_json(
    system_prompt: str,
    user_prompt: str,
    *,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """
    Call Groq and parse the response as JSON.

    Uses response_format=json_object so the model returns valid JSON.
    Retries transient API failures (5xx, connection) on the same model, then
    falls through to configured fallback models on any remaining error.
    """
    client = _get_client()
    primary = model or settings.groq_model
    candidates = _model_candidates(primary)

    last_exc: BaseException | None = None

    for index, model_name in enumerate(candidates):
        logger.info(
            "Groq request — model=%s%s",
            model_name,
            " (primary)" if index == 0 else " (fallback)",
        )
        try:
            response = await _create_completion(
                client,
                model_name=model_name,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            raw = response.choices[0].message.content or "{}"
            try:
                return json.loads(raw)
            except json.JSONDecodeError as e:
                last_exc = RuntimeError("LLM returned invalid JSON")
                last_exc.__cause__ = e
                logger.error(
                    "Groq model=%s returned invalid JSON: %s",
                    model_name,
                    raw[:500],
                )
        except BaseException as exc:
            last_exc = exc

        if index < len(candidates) - 1:
            logger.warning(
                "Groq failed on model=%s (%s) — trying fallback model=%s",
                model_name,
                last_exc,
                candidates[index + 1],
            )
            continue

        break

    assert last_exc is not None
    raise last_exc
