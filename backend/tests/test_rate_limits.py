"""Rate-limit surface — previously unlimited routes return 429 when exhausted."""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.services.analytics import events as analytics_events
from app.api.routes import waitlist as waitlist_route

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    waitlist_route.reset_memory_waitlist()
    analytics_events.reset_memory_analytics()
    monkeypatch.setattr(
        "app.persistence.supabase_repository.is_supabase_configured",
        lambda: False,
    )
    yield
    waitlist_route.reset_memory_waitlist()
    app.dependency_overrides.clear()


def test_waitlist_returns_429_when_rate_limit_exhausted(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_waitlist", "1/hour")

    first = client.post(
        "/api/waitlist",
        json={"email": "one@example.com", "name": "One"},
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/api/waitlist",
        json={"email": "two@example.com", "name": "Two"},
    )
    assert second.status_code == 429
