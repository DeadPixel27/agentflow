"""
Groq LLM client — thin wrapper around the Groq API.

Groq exposes an OpenAI-compatible chat API. We use it for structured
JSON extraction from document text.
"""

import json
import logging
from typing import Any, Optional

from groq import AsyncGroq

from app.config import settings

logger = logging.getLogger("llm")

_client: Optional[AsyncGroq] = None


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        if not settings.groq_api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to backend/.env"
            )
        _client = AsyncGroq(api_key=settings.groq_api_key)
    return _client


async def complete_json(
    system_prompt: str,
    user_prompt: str,
    *,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """
    Call Groq and parse the response as JSON.

    Uses response_format=json_object so the model returns valid JSON.
    """
    client = _get_client()
    model_name = model or settings.groq_model

    logger.info("Groq request — model=%s", model_name)

    response = await client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    raw = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Groq returned invalid JSON: %s", raw[:500])
        raise RuntimeError("LLM returned invalid JSON") from e
