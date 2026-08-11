from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.domain.email import EmailDeliveryError, EmailResult
from app.models.domain.run import RunResult
from app.models.domain.sheets import SheetsError, SheetsPushResult
from app.services.email.workflow_delivery import deliver_workflow_defaults
from app.services.usage import metering


@pytest.fixture(autouse=True)
def _isolate_usage(monkeypatch):
    monkeypatch.setattr(
        "app.persistence.supabase_repository.is_supabase_configured",
        lambda: False,
    )
    metering.reset_memory_usage()
    yield
    metering.reset_memory_usage()


def _run(**kwargs) -> RunResult:
    defaults = {
        "run_id": "run_1",
        "upload_id": "up_1",
        "task_description": "Extract invoices",
        "status": "completed",
        "steps": [],
        "document_ids": ["d1"],
        "workflow_id": "wf_1",
        "user_id": "u1",
    }
    defaults.update(kwargs)
    return RunResult(**defaults)


def _workflow(**kwargs) -> MagicMock:
    workflow = MagicMock()
    workflow.default_email = kwargs.get("default_email")
    workflow.default_sheets_url = kwargs.get("default_sheets_url")
    workflow.default_sheet_name = kwargs.get("default_sheet_name")
    return workflow


@pytest.mark.asyncio
async def test_deliver_skips_without_workflow():
    with (
        patch(
            "app.services.email.workflow_delivery.send_results_email",
            new_callable=AsyncMock,
        ) as send,
        patch(
            "app.services.email.workflow_delivery.push_rows_to_sheet",
            new_callable=AsyncMock,
        ) as push,
    ):
        await deliver_workflow_defaults(_run(workflow_id=None), [{"a": 1}])
    send.assert_not_called()
    push.assert_not_called()


@pytest.mark.asyncio
async def test_deliver_skips_without_rows():
    with (
        patch(
            "app.services.email.workflow_delivery.send_results_email",
            new_callable=AsyncMock,
        ) as send,
        patch(
            "app.services.email.workflow_delivery.push_rows_to_sheet",
            new_callable=AsyncMock,
        ) as push,
    ):
        await deliver_workflow_defaults(_run(), [])
    send.assert_not_called()
    push.assert_not_called()


@pytest.mark.asyncio
async def test_deliver_sends_when_default_email_set():
    mock_result = EmailResult(email_id="re_1", status="sent")

    with (
        patch(
            "app.services.email.workflow_delivery.get_workflow",
            return_value=_workflow(default_email="team@example.com"),
        ),
        patch(
            "app.services.email.workflow_delivery.send_results_email",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as send,
        patch(
            "app.services.email.workflow_delivery.push_rows_to_sheet",
            new_callable=AsyncMock,
        ) as push,
        patch(
            "app.services.analytics.events.log_event",
            new_callable=AsyncMock,
        ),
    ):
        await deliver_workflow_defaults(_run(), [{"vendor": "Acme"}])

    send.assert_awaited_once()
    push.assert_not_called()
    request = send.await_args.args[0]
    assert request.to_email == "team@example.com"
    assert request.rows == [{"vendor": "Acme"}]


@pytest.mark.asyncio
async def test_deliver_pushes_when_default_sheets_url_set():
    mock_result = SheetsPushResult(
        spreadsheet_id="ssid",
        sheet_name="Results",
        rows_written=1,
    )

    with (
        patch(
            "app.services.email.workflow_delivery.get_workflow",
            return_value=_workflow(
                default_sheets_url="https://docs.google.com/spreadsheets/d/abc"
            ),
        ),
        patch(
            "app.services.email.workflow_delivery.send_results_email",
            new_callable=AsyncMock,
        ) as send,
        patch(
            "app.services.email.workflow_delivery.push_rows_to_sheet",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as push,
        patch(
            "app.services.analytics.events.log_event",
            new_callable=AsyncMock,
        ),
    ):
        await deliver_workflow_defaults(_run(), [{"vendor": "Acme"}])

    send.assert_not_called()
    push.assert_awaited_once()
    assert push.await_args.args[0].endswith("/abc")
    assert push.await_args.kwargs["sheet_name"] == "Results"


@pytest.mark.asyncio
async def test_deliver_uses_custom_default_sheet_name():
    mock_result = SheetsPushResult(
        spreadsheet_id="ssid",
        sheet_name="Invoices",
        rows_written=1,
    )

    with (
        patch(
            "app.services.email.workflow_delivery.get_workflow",
            return_value=_workflow(
                default_sheets_url="https://docs.google.com/spreadsheets/d/abc",
                default_sheet_name="Invoices",
            ),
        ),
        patch(
            "app.services.email.workflow_delivery.send_results_email",
            new_callable=AsyncMock,
        ) as send,
        patch(
            "app.services.email.workflow_delivery.push_rows_to_sheet",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as push,
        patch(
            "app.services.analytics.events.log_event",
            new_callable=AsyncMock,
        ),
    ):
        await deliver_workflow_defaults(_run(), [{"vendor": "Acme"}])

    send.assert_not_called()
    push.assert_awaited_once()
    assert push.await_args.kwargs["sheet_name"] == "Invoices"


@pytest.mark.asyncio
async def test_deliver_skips_when_defaults_empty():
    with (
        patch(
            "app.services.email.workflow_delivery.get_workflow",
            return_value=_workflow(default_email="  ", default_sheets_url="  "),
        ),
        patch(
            "app.services.email.workflow_delivery.send_results_email",
            new_callable=AsyncMock,
        ) as send,
        patch(
            "app.services.email.workflow_delivery.push_rows_to_sheet",
            new_callable=AsyncMock,
        ) as push,
    ):
        await deliver_workflow_defaults(_run(), [{"a": 1}])

    send.assert_not_called()
    push.assert_not_called()


@pytest.mark.asyncio
async def test_deliver_swallows_email_and_sheets_errors():
    with (
        patch(
            "app.services.email.workflow_delivery.get_workflow",
            return_value=_workflow(
                default_email="team@example.com",
                default_sheets_url="https://docs.google.com/spreadsheets/d/abc",
            ),
        ),
        patch(
            "app.services.email.workflow_delivery.send_results_email",
            new_callable=AsyncMock,
            side_effect=EmailDeliveryError("boom"),
        ),
        patch(
            "app.services.email.workflow_delivery.push_rows_to_sheet",
            new_callable=AsyncMock,
            side_effect=SheetsError("boom"),
        ),
    ):
        await deliver_workflow_defaults(_run(), [{"a": 1}])


@pytest.mark.asyncio
async def test_deliver_skips_when_outbound_cap_hit(monkeypatch):
    from app.config import settings
    from app.services.usage import metering
    from app.services.usage.metering import EMAIL_EVENT_TYPE, SHEETS_EVENT_TYPE

    monkeypatch.setattr(
        "app.persistence.supabase_repository.is_supabase_configured",
        lambda: False,
    )
    metering.reset_memory_usage()
    monkeypatch.setattr(settings, "free_email_limit_monthly", 1)
    monkeypatch.setattr(settings, "free_sheets_limit_monthly", 1)
    await metering.record_usage("u1", 1, event_type=EMAIL_EVENT_TYPE)
    await metering.record_usage("u1", 1, event_type=SHEETS_EVENT_TYPE)

    with (
        patch(
            "app.services.email.workflow_delivery.get_workflow",
            return_value=_workflow(
                default_email="team@example.com",
                default_sheets_url="https://docs.google.com/spreadsheets/d/abc",
            ),
        ),
        patch(
            "app.services.email.workflow_delivery.send_results_email",
            new_callable=AsyncMock,
        ) as send,
        patch(
            "app.services.email.workflow_delivery.push_rows_to_sheet",
            new_callable=AsyncMock,
        ) as push,
    ):
        await deliver_workflow_defaults(_run(), [{"a": 1}])

    send.assert_not_awaited()
    push.assert_not_awaited()
    metering.reset_memory_usage()