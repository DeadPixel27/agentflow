import pytest
from unittest.mock import AsyncMock, patch

from app.agents.core.context import WorkflowContext
from app.agents.handlers.output.email_agent import EmailHandler
from app.models.domain.email import EmailResult


@pytest.mark.asyncio
async def test_email_agent_sends():
    ctx = WorkflowContext(upload_id="test", task_description="Extract invoices")
    ctx.data["rows"] = [{"vendor": "Acme", "amount": 5000}]
    ctx.data["documents"] = [{"document_id": "d1"}]
    ctx.data["user_id"] = "user-1"
    ctx.data["run_id"] = "run-1"
    config = {"to_email": "test@example.com", "subject": "Test"}

    mock_result = EmailResult(email_id="re_123", status="sent")
    with (
        patch(
            "app.agents.handlers.output.email_agent.reserve_outbound_usage",
            new_callable=AsyncMock,
        ) as reserve,
        patch(
            "app.agents.handlers.output.email_agent.send_results_email",
            new_callable=AsyncMock,
            return_value=mock_result,
        ),
    ):
        handler = EmailHandler()
        result = await handler.execute(ctx, config)

    reserve.assert_awaited_once()
    assert result.output["email_sent_to"] == "test@example.com"
    assert result.output["row_count"] == 1


@pytest.mark.asyncio
async def test_email_agent_requires_user_id():
    ctx = WorkflowContext(upload_id="test")
    ctx.data["rows"] = [{"vendor": "Acme"}]

    handler = EmailHandler()
    with pytest.raises(ValueError, match="metering"):
        await handler.execute(ctx, {"to_email": "test@example.com"})


@pytest.mark.asyncio
async def test_email_agent_blocks_when_over_cap(monkeypatch):
    from app.services.usage.metering import UsageLimitError

    ctx = WorkflowContext(upload_id="test")
    ctx.data["rows"] = [{"vendor": "Acme"}]
    ctx.data["user_id"] = "user-1"

    async def _raise(*_a, **_k):
        raise UsageLimitError("email cap")

    monkeypatch.setattr(
        "app.agents.handlers.output.email_agent.reserve_outbound_usage",
        _raise,
    )
    send = AsyncMock()
    monkeypatch.setattr(
        "app.agents.handlers.output.email_agent.send_results_email",
        send,
    )

    handler = EmailHandler()
    with pytest.raises(UsageLimitError):
        await handler.execute(ctx, {"to_email": "test@example.com"})
    send.assert_not_called()


@pytest.mark.asyncio
async def test_email_agent_requires_to_email():
    ctx = WorkflowContext(upload_id="test")
    ctx.data["rows"] = [{"vendor": "Acme"}]
    ctx.data["user_id"] = "user-1"

    handler = EmailHandler()
    with pytest.raises(ValueError, match="to_email"):
        await handler.execute(ctx, {})


@pytest.mark.asyncio
async def test_email_agent_requires_rows():
    ctx = WorkflowContext(upload_id="test")
    ctx.data["rows"] = []
    ctx.data["user_id"] = "user-1"

    handler = EmailHandler()
    with pytest.raises(ValueError, match="No rows"):
        await handler.execute(ctx, {"to_email": "test@example.com"})
