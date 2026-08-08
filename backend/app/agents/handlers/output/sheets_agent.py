"""Push extraction results to Google Sheets."""

from typing import Any

from app.agents.core.base import StepHandler, StepResult
from app.agents.core.context import WorkflowContext
from app.agents.core.registry import register_agent
from app.services.sheets.sheets_service import push_rows_to_sheet


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

        result = await push_rows_to_sheet(
            spreadsheet_url,
            rows,
            sheet_name=config.get("sheet_name", "AgentFlow Results"),
        )

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
