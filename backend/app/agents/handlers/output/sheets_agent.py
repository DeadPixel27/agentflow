"""Push extraction results to Google Sheets."""

from typing import Any

from app.agents.core.base import StepHandler, StepResult
from app.agents.core.context import WorkflowContext
from app.agents.core.registry import register_agent
from app.config import settings
from app.services.sheets.sheets_service import push_rows_to_sheet
from app.services.usage.metering import (
    SHEETS_EVENT_TYPE,
    refund_outbound_usage,
    reserve_outbound_usage,
)


class SheetsHandler(StepHandler):
    async def execute(
        self,
        ctx: WorkflowContext,
        config: dict[str, Any],
    ) -> StepResult:
        spreadsheet_url = config.get("spreadsheet_url")
        if not spreadsheet_url:
            raise ValueError("sheets agent config requires 'spreadsheet_url'")

        rows = ctx.data.get("rows", [])
        if not rows:
            raise ValueError("No rows available — run field_extractor first")

        user_id = ctx.data.get("user_id")
        run_id = ctx.data.get("run_id")
        if not user_id:
            raise ValueError("Cannot push to Sheets without user metering context")

        await reserve_outbound_usage(
            str(user_id),
            SHEETS_EVENT_TYPE,
            settings.free_sheets_limit_monthly,
            run_id=str(run_id) if run_id else None,
        )

        try:
            result = await push_rows_to_sheet(
                spreadsheet_url,
                rows,
                sheet_name=config.get("sheet_name", "Nexora Results"),
            )
        except Exception:
            try:
                await refund_outbound_usage(
                    str(user_id),
                    SHEETS_EVENT_TYPE,
                    run_id=str(run_id) if run_id else None,
                    reason="sheets_agent_failed",
                )
            except Exception:
                pass
            raise

        return StepResult(
            output={
                "spreadsheet_id": result.spreadsheet_id,
                "sheet_name": result.sheet_name,
                "rows_written": result.rows_written,
            }
        )


register_agent(
    "output.google_sheets",
    name="Google Sheets Agent",
    description=(
        "Push extraction results to a Google Sheets spreadsheet. "
        "Use when the user says 'sheets', 'spreadsheet', or 'google sheet'."
    ),
    example_config={
        "spreadsheet_url": "https://docs.google.com/spreadsheets/d/abc123/edit",
        "sheet_name": "Results",
    },
    handler=SheetsHandler(),
)
