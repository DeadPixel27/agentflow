"""Audit event writer (memory fallback)."""

import pytest

from app.logging_context import set_request_id
from app.services.audit import events as audit_events


@pytest.fixture(autouse=True)
def _reset_audit(monkeypatch):
    audit_events.reset_memory_audit()
    monkeypatch.setattr(
        "app.persistence.supabase_repository.is_supabase_configured",
        lambda: False,
    )
    yield
    audit_events.reset_memory_audit()


@pytest.mark.asyncio
async def test_log_audit_memory_includes_actor_and_request_id():
    set_request_id("abc123def456")
    await audit_events.log_audit(
        "auth.login",
        actor_user_id="user-1",
        resource_type="user",
        resource_id="user-1",
        metadata={"provider": "email"},
    )
    assert len(audit_events._memory_audit_events) == 1
    row = audit_events._memory_audit_events[0]
    assert row["action"] == "auth.login"
    assert row["actor_user_id"] == "user-1"
    assert row["request_id"] == "abc123def456"
    assert row["metadata"]["provider"] == "email"
    set_request_id("-")
