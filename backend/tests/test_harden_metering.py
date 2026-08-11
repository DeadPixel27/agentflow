"""Fail-closed metering: locks, 503 on record failure, outbound refund."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.dependencies import get_repo
from app.api.usage_http import charge_run_pages, reserve_email_usage
from app.config import settings
from app.main import app
from app.models.domain.email import EmailDeliveryError
from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult, StepRunRecord
from app.persistence.memory_repository import MemoryRepository
from app.services.analytics import events as analytics_events
from app.services.usage import metering
from app.services.usage.metering import (
    EMAIL_EVENT_TYPE,
    UsageLimitError,
    get_user_outbound_usage_this_month,
    reserve_page_usage,
)
from tests.auth_helpers import override_current_user

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    metering.reset_memory_usage()
    analytics_events.reset_memory_analytics()
    monkeypatch.setattr(
        "app.persistence.supabase_repository.is_supabase_configured",
        lambda: False,
    )
    monkeypatch.setattr(settings, "free_page_limit_monthly", 50)
    monkeypatch.setattr(settings, "global_daily_page_limit", 500)
    monkeypatch.setattr(settings, "free_email_limit_monthly", 20)
    yield
    metering.reset_memory_usage()
    analytics_events.reset_memory_analytics()
    app.dependency_overrides.clear()


def _completed_run(*, user_id: str = "user-1") -> RunResult:
    return RunResult(
        run_id="run-1",
        upload_id="upload-1",
        task_description="Extract invoices",
        status="completed",
        steps=[
            StepRunRecord(
                step_order=1,
                agent_type="transform.field_extractor",
                status="completed",
            )
        ],
        planned_steps=[
            PlannedStep(
                step_order=1,
                agent_type="transform.field_extractor",
                config={"fields": ["vendor"]},
                reason="extract",
            )
        ],
        document_ids=["doc-1"],
        user_id=user_id,
        result={"rows": [{"vendor": "Acme", "amount": 100}]},
    )


@pytest.mark.asyncio
async def test_charge_run_pages_raises_503_when_record_fails(monkeypatch):
    async def _boom(*_a, **_k):
        raise RuntimeError("db insert failed")

    monkeypatch.setattr(
        "app.api.usage_http.reserve_page_usage",
        _boom,
    )

    with pytest.raises(HTTPException) as exc_info:
        await charge_run_pages("user-1", page_count=2, run_id="run-x")
    assert exc_info.value.status_code == 503
    assert "Unable to record usage" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_reserve_page_usage_second_call_fails_under_cap(monkeypatch):
    monkeypatch.setattr(settings, "free_page_limit_monthly", 5)

    await reserve_page_usage("user-1", 5, run_id="run-a")
    with pytest.raises(UsageLimitError):
        await reserve_page_usage("user-1", 1, run_id="run-b")


@pytest.mark.asyncio
async def test_concurrent_reserves_do_not_overshoot_cap(monkeypatch):
    monkeypatch.setattr(settings, "free_page_limit_monthly", 5)

    results: list[str] = []

    async def _try_reserve(label: str) -> None:
        try:
            await reserve_page_usage("user-lock", 3, run_id=label)
            results.append("ok")
        except UsageLimitError:
            results.append("limit")

    await asyncio.gather(_try_reserve("a"), _try_reserve("b"))
    assert results.count("ok") == 1
    assert results.count("limit") == 1
    assert await metering.get_user_usage_this_month("user-lock") == 3


@pytest.mark.asyncio
async def test_email_route_refunds_on_provider_failure(monkeypatch):
    repo = MemoryRepository()
    repo.save_run(_completed_run())
    app.dependency_overrides[get_repo] = lambda: repo
    override_current_user()

    monkeypatch.setattr(
        "app.api.routes.email.send_results_email",
        AsyncMock(side_effect=EmailDeliveryError("resend down")),
    )

    response = client.post(
        "/api/runs/run-1/email",
        json={"to_email": "team@example.com", "subject": "Results"},
    )
    assert response.status_code == 502
    used = await get_user_outbound_usage_this_month("user-1", EMAIL_EVENT_TYPE)
    assert used == 0


@pytest.mark.asyncio
async def test_reserve_email_usage_raises_503_when_record_fails(monkeypatch):
    async def _boom(*_a, **_k):
        raise RuntimeError("db insert failed")

    monkeypatch.setattr(
        "app.api.usage_http.reserve_outbound_usage",
        _boom,
    )

    with pytest.raises(HTTPException) as exc_info:
        await reserve_email_usage("user-1", run_id="run-1")
    assert exc_info.value.status_code == 503
