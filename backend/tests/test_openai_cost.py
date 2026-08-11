"""OpenAI usage estimate + daily budget gate."""

from types import SimpleNamespace

import pytest

from app.services.llm import openai_cost
from app.services.llm.openai_cost import (
    OpenAIBudgetError,
    OpenAIUsageEstimate,
    check_openai_budget_allowed,
    estimate_from_response,
    estimate_usd,
    get_openai_spend_today,
    prices_for_model,
    record_openai_usage,
    reset_openai_spend_tracker,
)


@pytest.fixture(autouse=True)
def _reset_spend():
    reset_openai_spend_tracker()
    yield
    reset_openai_spend_tracker()


def test_prices_for_known_and_prefix_models():
    assert prices_for_model("gpt-4o") == (2.50, 10.00)
    assert prices_for_model("gpt-4o-mini") == (0.15, 0.60)
    assert prices_for_model("gpt-4o-mini-2024-07-18") == (0.15, 0.60)


def test_estimate_usd_gpt4o():
    # 1M in + 1M out = $2.50 + $10
    assert estimate_usd("gpt-4o", 1_000_000, 1_000_000) == pytest.approx(12.50)
    # Typical extract-ish: 2500 in + 400 out
    cost = estimate_usd("gpt-4o", 2500, 400)
    assert cost == pytest.approx(0.01025)


def test_estimate_from_response():
    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=1000,
            completion_tokens=200,
            total_tokens=1200,
        )
    )
    est = estimate_from_response("gpt-4o", response)
    assert est is not None
    assert est.prompt_tokens == 1000
    assert est.completion_tokens == 200
    assert est.estimated_usd == pytest.approx(0.0045)


def test_record_and_budget_gate(monkeypatch):
    monkeypatch.setattr(
        openai_cost.settings, "openai_daily_budget_usd", 0.01
    )
    check_openai_budget_allowed()  # under budget

    record_openai_usage(
        OpenAIUsageEstimate(
            model="gpt-4o",
            prompt_tokens=2000,
            completion_tokens=500,
            total_tokens=2500,
            estimated_usd=0.01,
        )
    )
    snap = get_openai_spend_today()
    assert snap["calls"] == 1
    assert snap["estimated_usd"] == pytest.approx(0.01)

    with pytest.raises(OpenAIBudgetError):
        check_openai_budget_allowed()


def test_budget_disabled_when_zero(monkeypatch):
    monkeypatch.setattr(openai_cost.settings, "openai_daily_budget_usd", 0.0)
    record_openai_usage(
        OpenAIUsageEstimate(
            model="gpt-4o",
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
            total_tokens=2_000_000,
            estimated_usd=12.5,
        )
    )
    check_openai_budget_allowed()  # must not raise
