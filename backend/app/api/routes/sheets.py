"""Google Sheets push route — append run results to a spreadsheet."""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import RepoDep
from app.models.api.sheets import SheetsPushRequest, SheetsPushResponse
from app.models.domain.sheets import SheetsError
from app.services.sheets.sheets_service import push_rows_to_sheet

router = APIRouter(prefix="/api/runs", tags=["sheets"])


@router.post("/{run_id}/sheets", response_model=SheetsPushResponse)
async def push_run_to_sheets(
    run_id: str,
    body: SheetsPushRequest,
    repo: RepoDep,
) -> SheetsPushResponse:
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    if run.status != "completed":
        raise HTTPException(status_code=400, detail="Run is not completed yet")

    result_data = run.result or {}
    rows = result_data.get("rows", [])
    if not rows:
        raise HTTPException(status_code=400, detail="Run has no result rows")

    try:
        result = await push_rows_to_sheet(
            body.spreadsheet_url,
            rows,
            sheet_name=body.sheet_name,
        )
    except SheetsError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return SheetsPushResponse(
        status="pushed",
        spreadsheet_id=result.spreadsheet_id,
        sheet_name=result.sheet_name,
        rows_written=result.rows_written,
    )
