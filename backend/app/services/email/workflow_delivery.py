"""Post-run delivery for workflow defaults (email + sheets)."""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.models.domain.email import EmailDeliveryError, EmailRequest
from app.models.domain.run import RunResult
from app.models.domain.sheets import SheetsError
from app.persistence import get_workflow
from app.services.email.email_service import send_results_email
from app.services.sheets.sheets_service import push_rows_to_sheet
from app.services.usage.metering import (
    EMAIL_EVENT_TYPE,
    SHEETS_EVENT_TYPE,
    UsageLimitError,
    refund_outbound_usage,
    reserve_outbound_usage,
)

logger = logging.getLogger("workflow_delivery")

_DEFAULT_SHEET_NAME = "Results"


async def deliver_workflow_defaults(
    run: RunResult,
    rows: list[dict[str, Any]],
) -> None:
    """Send default deliveries after a successful workflow run.

    Failures are logged and swallowed so extraction success is preserved.
    """
    if not run.workflow_id or not rows:
        return

    workflow = get_workflow(run.workflow_id)
    if workflow is None:
        return

    default_email = (workflow.default_email or "").strip()
    if default_email:
        await _send_default_email(run, rows, default_email)

    default_sheets_url = (workflow.default_sheets_url or "").strip()
    if default_sheets_url:
        await _push_default_sheets(run, rows, default_sheets_url)


async def _send_default_email(
    run: RunResult,
    rows: list[dict[str, Any]],
    to_email: str,
) -> None:
    user_id = run.user_id
    reserved = False
    if user_id:
        try:
            await reserve_outbound_usage(
                user_id,
                EMAIL_EVENT_TYPE,
                settings.free_email_limit_monthly,
                run_id=run.run_id,
            )
            reserved = True
        except UsageLimitError as exc:
            logger.warning(
                "Auto-email skipped for run %s — outbound cap: %s",
                run.run_id,
                exc,
            )
            return
        except Exception as exc:
            logger.warning(
                "Auto-email skipped for run %s — could not reserve usage: %s",
                run.run_id,
                exc,
            )
            return

    pipeline_name = (run.task_description or "Workflow results")[:80]
    subject = f"{pipeline_name} — Results"
    request = EmailRequest(
        to_email=to_email,
        subject=subject,
        rows=rows,
        pipeline_name=pipeline_name,
        doc_count=len(run.document_ids),
    )
    try:
        result = await send_results_email(request)
        logger.info(
            "Auto-emailed run %s to %s (email_id=%s)",
            run.run_id,
            to_email,
            result.email_id,
        )
        try:
            from app.services.analytics.events import log_event

            await log_event(
                "delivery_email_sent",
                user_id=run.user_id,
                run_id=run.run_id,
                metadata={
                    "workflow_id": run.workflow_id,
                    "email_id": result.email_id,
                },
            )
        except Exception:
            pass
    except EmailDeliveryError as exc:
        if reserved and user_id:
            try:
                await refund_outbound_usage(
                    user_id,
                    EMAIL_EVENT_TYPE,
                    run_id=run.run_id,
                    reason="email_failed",
                )
            except Exception:
                logger.warning(
                    "Failed to refund auto-email usage for run %s",
                    run.run_id,
                    exc_info=True,
                )
        logger.error(
            "Auto-email failed for run %s to %s: %s",
            run.run_id,
            to_email,
            exc,
        )
    except Exception as exc:
        if reserved and user_id:
            try:
                await refund_outbound_usage(
                    user_id,
                    EMAIL_EVENT_TYPE,
                    run_id=run.run_id,
                    reason="email_failed",
                )
            except Exception:
                logger.warning(
                    "Failed to refund auto-email usage for run %s",
                    run.run_id,
                    exc_info=True,
                )
        logger.error(
            "Unexpected auto-email error for run %s: %s",
            run.run_id,
            exc,
        )


async def _push_default_sheets(
    run: RunResult,
    rows: list[dict[str, Any]],
    spreadsheet_url: str,
) -> None:
    user_id = run.user_id
    reserved = False
    if user_id:
        try:
            await reserve_outbound_usage(
                user_id,
                SHEETS_EVENT_TYPE,
                settings.free_sheets_limit_monthly,
                run_id=run.run_id,
            )
            reserved = True
        except UsageLimitError as exc:
            logger.warning(
                "Auto-sheets skipped for run %s — outbound cap: %s",
                run.run_id,
                exc,
            )
            return
        except Exception as exc:
            logger.warning(
                "Auto-sheets skipped for run %s — could not reserve usage: %s",
                run.run_id,
                exc,
            )
            return

    try:
        result = await push_rows_to_sheet(
            spreadsheet_url,
            rows,
            sheet_name=_DEFAULT_SHEET_NAME,
        )
        logger.info(
            "Auto-pushed run %s to sheets %s (%d rows)",
            run.run_id,
            result.spreadsheet_id,
            result.rows_written,
        )
        try:
            from app.services.analytics.events import log_event

            await log_event(
                "delivery_sheets_pushed",
                user_id=run.user_id,
                run_id=run.run_id,
                metadata={
                    "workflow_id": run.workflow_id,
                    "spreadsheet_id": result.spreadsheet_id,
                    "sheet_name": result.sheet_name,
                    "rows_written": result.rows_written,
                },
            )
        except Exception:
            pass
    except SheetsError as exc:
        if reserved and user_id:
            try:
                await refund_outbound_usage(
                    user_id,
                    SHEETS_EVENT_TYPE,
                    run_id=run.run_id,
                    reason="sheets_failed",
                )
            except Exception:
                logger.warning(
                    "Failed to refund auto-sheets usage for run %s",
                    run.run_id,
                    exc_info=True,
                )
        logger.error(
            "Auto-sheets failed for run %s: %s",
            run.run_id,
            exc,
        )
    except Exception as exc:
        if reserved and user_id:
            try:
                await refund_outbound_usage(
                    user_id,
                    SHEETS_EVENT_TYPE,
                    run_id=run.run_id,
                    reason="sheets_failed",
                )
            except Exception:
                logger.warning(
                    "Failed to refund auto-sheets usage for run %s",
                    run.run_id,
                    exc_info=True,
                )
        logger.error(
            "Unexpected auto-sheets error for run %s: %s",
            run.run_id,
            exc,
        )
