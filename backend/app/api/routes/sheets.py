"""Google Sheets push route — append run results to a spreadsheet."""

from fastapi import APIRouter, HTTPException, Request

from app.api.dependencies import CurrentUserDep, RepoDep
from app.api.ownership import require_run_access
from app.api.usage_http import refund_sheets_usage, reserve_sheets_usage
from app.config import settings
from app.models.api.sheets import SheetsPushRequest, SheetsPushResponse
from app.models.domain.sheets import SheetsError
from app.rate_limit import limiter
from app.services.sheets.sheets_service import push_rows_to_sheet

router = APIRouter(prefix="/api/runs", tags=["sheets"])


@router.post("/{run_id}/sheets", response_model=SheetsPushResponse)
@limiter.limit(settings.rate_limit_sheets)
async def push_run_to_sheets(
    request: Request,
    run_id: str,
    body: SheetsPushRequest,
    repo: RepoDep,
    current_user: CurrentUserDep,
) -> SheetsPushResponse:
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    await require_run_access(run, current_user, repo)
    if run.status != "completed":
        raise HTTPException(status_code=400, detail="Run is not completed yet")

    result_data = run.result or {}
    rows = result_data.get("rows", [])
    if not rows:
        raise HTTPException(status_code=400, detail="Run has no result rows")

    await reserve_sheets_usage(current_user.user_id, run_id=run_id)

    try:
        result = await push_rows_to_sheet(
            body.spreadsheet_url,
            rows,
            sheet_name=body.sheet_name,
        )
    except SheetsError as exc:
        await refund_sheets_usage(current_user.user_id, run_id=run_id)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    from app.services.audit.events import log_audit

    await log_audit(
        "delivery.sheets",
        actor_user_id=current_user.user_id,
        resource_type="run",
        resource_id=run_id,
        metadata={"spreadsheet_id": result.spreadsheet_id, "source": "manual"},
    )

    return SheetsPushResponse(
        status="pushed",
        spreadsheet_id=result.spreadsheet_id,
        sheet_name=result.sheet_name,
        rows_written=result.rows_written,
    )
