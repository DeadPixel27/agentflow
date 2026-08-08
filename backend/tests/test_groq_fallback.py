"""Tests for Groq client model fallback."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from groq import APIStatusError, RateLimitError

from app.services.llm import groq_client


def _mock_response(payload: str):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=payload))]
    )


def _rate_limit_error() -> RateLimitError:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(429, request=request)
    return RateLimitError("rate limited", response=response, body=None)


def _server_error() -> APIStatusError:
    request = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    response = httpx.Response(500, request=request)
    return APIStatusError("server error", response=response, body=None)


@pytest.mark.asyncio
async def test_complete_json_uses_primary_when_available(monkeypatch):
    create = AsyncMock(return_value=_mock_response('{"ok": true}'))
    monkeypatch.setattr(groq_client, "_create_completion", create)
    monkeypatch.setattr(
        groq_client.settings,
        "groq_fallback_models",
        "llama-3.1-8b-instant",
    )

    result = await groq_client.complete_json("sys", "user", model="primary-model")

    assert result == {"ok": True}
    create.assert_awaited_once()
    assert create.await_args.kwargs["model_name"] == "primary-model"


@pytest.mark.asyncio
async def test_complete_json_falls_back_on_429(monkeypatch):
    create = AsyncMock(
        side_effect=[
            _rate_limit_error(),
            _mock_response('{"fallback": true}'),
        ]
    )
    monkeypatch.setattr(groq_client, "_create_completion", create)
    monkeypatch.setattr(
        groq_client.settings,
        "groq_fallback_models",
        "llama-3.1-8b-instant",
    )

    result = await groq_client.complete_json("sys", "user", model="primary-model")

    assert result == {"fallback": True}
    assert create.await_count == 2
    assert create.await_args_list[0].kwargs["model_name"] == "primary-model"
    assert (
        create.await_args_list[1].kwargs["model_name"] == "llama-3.1-8b-instant"
    )


@pytest.mark.asyncio
async def test_complete_json_falls_back_on_server_error(monkeypatch):
    create = AsyncMock(
        side_effect=[
            _server_error(),
            _mock_response('{"fallback": true}'),
        ]
    )
    monkeypatch.setattr(groq_client, "_create_completion", create)
    monkeypatch.setattr(
        groq_client.settings,
        "groq_fallback_models",
        "llama-3.1-8b-instant",
    )

    result = await groq_client.complete_json("sys", "user", model="primary-model")

    assert result == {"fallback": True}
    assert create.await_count == 2


@pytest.mark.asyncio
async def test_complete_json_falls_back_on_invalid_json(monkeypatch):
    create = AsyncMock(
        side_effect=[
            _mock_response("not-json"),
            _mock_response('{"fallback": true}'),
        ]
    )
    monkeypatch.setattr(groq_client, "_create_completion", create)
    monkeypatch.setattr(
        groq_client.settings,
        "groq_fallback_models",
        "llama-3.1-8b-instant",
    )

    result = await groq_client.complete_json("sys", "user", model="primary-model")

    assert result == {"fallback": True}
    assert create.await_count == 2


@pytest.mark.asyncio
async def test_complete_json_raises_when_all_models_fail(monkeypatch):
    create = AsyncMock(side_effect=_rate_limit_error())
    monkeypatch.setattr(groq_client, "_create_completion", create)
    monkeypatch.setattr(
        groq_client.settings,
        "groq_fallback_models",
        "llama-3.1-8b-instant",
    )

    with pytest.raises(RateLimitError):
        await groq_client.complete_json("sys", "user", model="primary-model")

    assert create.await_count == 2


def test_model_candidates_dedupes_primary_from_fallbacks(monkeypatch):
    monkeypatch.setattr(
        groq_client.settings,
        "groq_fallback_models",
        "llama-3.3-70b-versatile,llama-3.1-8b-instant,llama-3.1-8b-instant",
    )

    candidates = groq_client._model_candidates("llama-3.3-70b-versatile")
    assert candidates == [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ]
