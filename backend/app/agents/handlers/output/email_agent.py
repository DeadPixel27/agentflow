"""Send extraction results via email."""

from typing import Any

from app.agents.core.base import StepHandler, StepResult
from app.agents.core.context import WorkflowContext
from app.agents.core.registry import register_agent
from app.models.domain.email import EmailRequest
from app.services.email.email_service import send_results_email


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

        request = EmailRequest(
            to_email=to_email,
            subject=config.get("subject", "Your Nexora Results"),
            rows=rows,
            pipeline_name=ctx.task_description[:80],
            doc_count=len(ctx.data.get("documents", [])),
        )
        result = await send_results_email(request)

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
