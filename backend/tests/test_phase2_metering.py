"""Phase 2 smoke tests — usage metering, waitlist, analytics, caps."""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.domain.run import RunResult
from app.persistence.memory_repository import MemoryRepository
from app.services.analytics import events as analytics_events
from app.services.usage import metering
from app.services.usage.metering import (
    GlobalCapError,
    RefineLimitError,
    UsageLimitError,
    check_refine_allowed,
    check_usage_allowed,
    get_usage_summary,
    record_usage,
)
from tests.auth_helpers import auth_user, override_current_user

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_phase2_state(monkeypatch):
    metering.reset_memory_usage()
    analytics_events.reset_memory_analytics()
    from app.api.routes import waitlist as waitlist_route

    waitlist_route.reset_memory_waitlist()
    # Force in-memory path even if local .env has Supabase credentials
    monkeypatch.setattr(
        "app.persistence.supabase_repository.is_supabase_configured",
        lambda: False,
    )
    monkeypatch.setattr(settings, "free_page_limit_monthly", 50)
    monkeypatch.setattr(settings, "global_daily_page_limit", 500)
    monkeypatch.setattr(settings, "max_refines_per_run", 10)
    yield
    metering.reset_memory_usage()
    analytics_events.reset_memory_analytics()
    waitlist_route.reset_memory_waitlist()
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_record_and_summarize_usage():
    await record_usage("user-1", 3, run_id="run-a")
    await record_usage("user-1", 2, run_id="run-b")
    summary = await get_usage_summary("user-1")
    assert summary["pages_used"] == 5
    assert summary["pages_limit"] == 50
    assert summary["resets_at"]


@pytest.mark.asyncio
async def test_monthly_cap_raises_usage_limit_error(monkeypatch):
    monkeypatch.setattr(settings, "free_page_limit_monthly", 5)
    await record_usage("user-1", 5)
    with pytest.raises(UsageLimitError):
        await check_usage_allowed("user-1", 1)


@pytest.mark.asyncio
async def test_global_cap_raises_503_style_error(monkeypatch):
    monkeypatch.setattr(settings, "global_daily_page_limit", 4)
    await record_usage("user-a", 2)
    await record_usage("user-b", 2)
    with pytest.raises(GlobalCapError):
        await check_usage_allowed("user-c", 1)


@pytest.mark.asyncio
async def test_refine_limit(monkeypatch):
    monkeypatch.setattr(settings, "max_refines_per_run", 2)
    repo = MemoryRepository()
    parent = "parent-run"
    repo.save_run(
        RunResult(
            run_id="child-1",
            upload_id="u1",
            task_description="",
            status="completed",
            steps=[],
            parent_run_id=parent,
        )
    )
    repo.save_run(
        RunResult(
            run_id="child-2",
            upload_id="u1",
            task_description="",
            status="completed",
            steps=[],
            parent_run_id=parent,
        )
    )
    monkeypatch.setattr("app.persistence.get_repository", lambda: repo)

    with pytest.raises(RefineLimitError):
        await check_refine_allowed(parent)


def test_waitlist_public_and_dedupes():
    first = client.post(
        "/api/waitlist",
        json={"email": "pro@example.com", "name": "Pro", "source": "pricing_page"},
    )
    assert first.status_code == 200, first.text
    assert first.json()["already_joined"] is False

    second = client.post(
        "/api/waitlist",
        json={"email": "pro@example.com", "name": "Pro"},
    )
    assert second.status_code == 200
    assert second.json()["already_joined"] is True


def test_waitlist_requires_no_auth():
    response = client.post(
        "/api/waitlist",
        json={"email": "anon@example.com"},
    )
    assert response.status_code == 200


def test_usage_endpoint_requires_auth():
    response = client.get("/api/users/me/usage")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_usage_endpoint_returns_summary():
    override_current_user(auth_user(user_id="user-usage"))
    await record_usage("user-usage", 7)

    response = client.get("/api/users/me/usage")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["pages_used"] == 7
    assert body["pages_limit"] == 50


@pytest.mark.asyncio
async def test_run_adhoc_returns_429_when_over_monthly_cap(monkeypatch):
    monkeypatch.setattr(settings, "free_page_limit_monthly", 1)
    await record_usage("user-1", 1)
    override_current_user()

    response = client.post(
        "/api/runs/adhoc",
        json={"upload_id": "missing", "task_description": "extract fields"},
    )
    assert response.status_code == 429
    detail = response.json()["detail"].lower()
    assert "free pages" in detail or "used" in detail


@pytest.mark.asyncio
async def test_analytics_log_event_memory():
    await analytics_events.log_event(
        "run_started",
        user_id="user-1",
        run_id="run-1",
        page_count=2,
    )
    assert len(analytics_events._memory_analytics_events) == 1
    assert analytics_events._memory_analytics_events[0]["event_type"] == "run_started"
