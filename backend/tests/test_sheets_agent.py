import pytest
from unittest.mock import AsyncMock, patch

from app.agents.core.context import WorkflowContext
from app.agents.handlers.output.sheets_agent import SheetsHandler
from app.models.domain.sheets import SheetsPushResult


@pytest.mark.asyncio
async def test_sheets_agent_pushes():
    ctx = WorkflowContext(upload_id="test", task_description="Extract invoices")
    ctx.data["rows"] = [{"vendor": "Acme", "amount": 5000}]
    ctx.data["user_id"] = "user-1"
    ctx.data["run_id"] = "run-1"
    config = {
        "spreadsheet_url": "https://docs.google.com/spreadsheets/d/abc123/edit",
        "sheet_name": "Test Sheet",
    }

    mock_result = SheetsPushResult(
        spreadsheet_id="abc123", sheet_name="Test Sheet", rows_written=1
    )
    with (
        patch(
            "app.agents.handlers.output.sheets_agent.reserve_outbound_usage",
            new_callable=AsyncMock,
        ) as reserve,
        patch(
            "app.agents.handlers.output.sheets_agent.push_rows_to_sheet",
            new_callable=AsyncMock,
            return_value=mock_result,
        ),
    ):
        handler = SheetsHandler()
        result = await handler.execute(ctx, config)

    reserve.assert_awaited_once()
    assert result.output["spreadsheet_id"] == "abc123"
    assert result.output["rows_written"] == 1


@pytest.mark.asyncio
async def test_sheets_agent_requires_user_id():
    ctx = WorkflowContext(upload_id="test")
    ctx.data["rows"] = [{"vendor": "Acme"}]

    handler = SheetsHandler()
    with pytest.raises(ValueError, match="metering"):
        await handler.execute(
            ctx,
            {"spreadsheet_url": "https://docs.google.com/spreadsheets/d/abc123/edit"},
        )


@pytest.mark.asyncio
async def test_sheets_agent_requires_url():
    ctx = WorkflowContext(upload_id="test")
    ctx.data["rows"] = [{"vendor": "Acme"}]
    ctx.data["user_id"] = "user-1"

    handler = SheetsHandler()
    with pytest.raises(ValueError, match="spreadsheet_url"):
        await handler.execute(ctx, {})


@pytest.mark.asyncio
async def test_sheets_agent_requires_rows():
    ctx = WorkflowContext(upload_id="test")
    ctx.data["rows"] = []
    ctx.data["user_id"] = "user-1"

    handler = SheetsHandler()
    with pytest.raises(ValueError, match="No rows"):
        await handler.execute(ctx, {"spreadsheet_url": "https://..."})


def test_a1_range_quotes_sheet_names_with_spaces():
    from app.services.sheets.sheets_service import _a1_range

    assert _a1_range("Nexora Results") == "'Nexora Results'!A1"
    assert _a1_range("Results") == "Results!A1"
    assert _a1_range("O'Brien") == "'O''Brien'!A1"
