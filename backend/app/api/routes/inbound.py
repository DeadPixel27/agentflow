"""Inbound email webhook — receives forwarded emails from Mailgun/Resend."""

import hashlib
import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.api.dependencies import InboundEmailServiceDep, WorkflowServiceDep
from app.api.usage_http import enforce_upload_usage, record_run_usage
from app.config import settings
from app.models.domain.email import InboundAddressNotFoundError
from app.services.documents.upload_loader import UploadNotFoundError
from app.services.pipeline.runner import execute_run
from app.services.workflows.workflow_service import WorkflowNotFoundError

router = APIRouter(prefix="/api/inbound", tags=["inbound"])
logger = logging.getLogger("inbound")


def _verify_mailgun_signature(
    token: str, timestamp: str, signature: str
) -> bool:
    """Verify Mailgun webhook signature. Fail closed when secret is unset."""
    if not settings.inbound_webhook_secret:
        logger.error("INBOUND_WEBHOOK_SECRET is not set — rejecting webhook")
        return False
    hmac_digest = hmac.new(
        key=settings.inbound_webhook_secret.encode(),
        msg=f"{timestamp}{token}".encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, hmac_digest)


@router.post("/email")
async def receive_inbound_email(
    request: Request,
    background_tasks: BackgroundTasks,
    inbound: InboundEmailServiceDep,
    workflows: WorkflowServiceDep,
):
    """Mailgun posts here when email arrives at *@ingest.agentflow.app."""
    form = await request.form()

    if not _verify_mailgun_signature(
        str(form.get("token", "")),
        str(form.get("timestamp", "")),
        str(form.get("signature", "")),
    ):
        raise HTTPException(status_code=403, detail="Invalid signature")

    recipient = str(form.get("recipient", ""))
    sender = str(form.get("sender", ""))

    attachments = []
    for key in form:
        if key.startswith("attachment-"):
            file = form[key]
            content = await file.read()
            attachments.append({
                "filename": file.filename,
                "content": content,
                "content_type": file.content_type or "application/octet-stream",
            })

    try:
        upload_id, workflow_id, _reply_to, owner_user_id = await inbound.process_inbound(
            recipient, sender, attachments
        )
        page_count = await enforce_upload_usage(owner_user_id, upload_id)
        run = await workflows.start_workflow_run(workflow_id, upload_id)
        background_tasks.add_task(execute_run, run.run_id)
        await record_run_usage(
            owner_user_id,
            page_count=page_count,
            run_id=run.run_id,
            template_id=getattr(run, "template_id", None),
            event_type="inbound_email",
        )
        return {"status": "processing", "run_id": run.run_id}
    except InboundAddressNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (WorkflowNotFoundError, UploadNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
