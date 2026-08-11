"""Send extraction results via email."""

from typing import Any

from app.agents.core.base import StepHandler, StepResult
from app.agents.core.context import WorkflowContext
from app.agents.core.registry import register_agent
from app.config import settings
from app.models.domain.email import EmailRequest
from app.services.email.email_service import send_results_email
from app.services.usage.metering import (
    EMAIL_EVENT_TYPE,
    refund_outbound_usage,
    reserve_outbound_usage,
)


class EmailHandler(StepHandler):
    async def execute(
        self,
        ctx: WorkflowContext,
        config: dict[str, Any],
    ) -> StepResult:
        to_email = config.get("to_email")
        if not to_email:
            raise ValueError("email agent config requires 'to_email'")

        rows = ctx.data.get("rows", [])
        if not rows:
            raise ValueError("No rows available — run field_extractor first")

        user_id = ctx.data.get("user_id")
        run_id = ctx.data.get("run_id")
        if not user_id:
            raise ValueError("Cannot send email without user metering context")

        await reserve_outbound_usage(
            str(user_id),
            EMAIL_EVENT_TYPE,
            settings.free_email_limit_monthly,
            run_id=str(run_id) if run_id else None,
        )

        request = EmailRequest(
            to_email=to_email,
            subject=config.get("subject", "Your Nexora Results"),
            rows=rows,
            pipeline_name=ctx.task_description[:80],
            doc_count=len(ctx.data.get("documents", [])),
        )
        try:
            result = await send_results_email(request)
        except Exception:
            try:
                await refund_outbound_usage(
                    str(user_id),
                    EMAIL_EVENT_TYPE,
                    run_id=str(run_id) if run_id else None,
                    reason="email_agent_failed",
                )
            except Exception:
                pass
            raise

        return StepResult(
            output={
                "email_sent_to": to_email,
                "email_id": result.email_id,
                "row_count": len(rows),
            }
        )


register_agent(
    "output.email",
    name="Email Agent",
    description=(
        "Send extraction results via email. "
        "Includes an HTML table in the body and a CSV attachment. "
        "Use when the user says 'email', 'send to', or 'deliver to'."
    ),
    example_config={
        "to_email": "user@example.com",
        "subject": "Invoice Extraction Results",
    },
    handler=EmailHandler(),
)
