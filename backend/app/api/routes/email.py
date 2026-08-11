"""Email delivery route — send run results to an email address."""

from fastapi import APIRouter, HTTPException, Request

from app.api.dependencies import CurrentUserDep, RepoDep
from app.api.ownership import require_run_access
from app.api.usage_http import refund_email_usage, reserve_email_usage
from app.config import settings
from app.models.api.email import EmailResultsRequest, EmailResultsResponse
from app.models.domain.email import EmailDeliveryError, EmailRequest
from app.rate_limit import limiter
from app.services.email.email_service import send_results_email

router = APIRouter(prefix="/api/runs", tags=["email"])


@router.post("/{run_id}/email", response_model=EmailResultsResponse)
@limiter.limit(settings.rate_limit_email)
async def email_run_results(
    request: Request,
    run_id: str,
    body: EmailResultsRequest,
    repo: RepoDep,
    current_user: CurrentUserDep,
) -> EmailResultsResponse:
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

    await reserve_email_usage(current_user.user_id, run_id=run_id)

    request_payload = EmailRequest(
        to_email=str(body.to_email),
        subject=body.subject,
        rows=rows,
        pipeline_name=run.task_description[:80],
        doc_count=len(run.document_ids),
    )

    try:
        result = await send_results_email(request_payload)
    except EmailDeliveryError as exc:
        await refund_email_usage(current_user.user_id, run_id=run_id)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return EmailResultsResponse(
        status="sent",
        email_id=result.email_id,
        message=f"Results emailed to {body.to_email}",
    )
