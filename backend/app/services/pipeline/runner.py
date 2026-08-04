"""
Workflow runner — executes an ordered list of steps against an upload.
"""

import logging
import uuid
from typing import Optional

import app.agents.handlers  # noqa: F401 — register agents
from app.agents.core.context import WorkflowContext, documents_to_dicts
from app.agents.core.registry import get_handler
from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult, StepRunRecord
from app.services.documents.upload_loader import load_upload_documents

logger = logging.getLogger("runner")


async def run_pipeline(
    upload_id: str,
    steps: list[PlannedStep],
    task_description: str = "",
    workflow_id: Optional[str] = None,
) -> RunResult:
    """Execute all steps in order and return the final run result."""
    run_id = str(uuid.uuid4())
    documents = await load_upload_documents(upload_id)
    if not documents:
        raise ValueError(f"No documents found for upload {upload_id}")

    document_ids = [doc.document_id for doc in documents]

    ctx = WorkflowContext(
        upload_id=upload_id,
        task_description=task_description,
        data={"documents": documents_to_dicts(documents)},
    )

    step_runs: list[StepRunRecord] = []
    sorted_steps = sorted(steps, key=lambda s: s.step_order)

    logger.info(
        "Run %s started — upload_id=%s, %d step(s)",
        run_id,
        upload_id,
        len(sorted_steps),
    )

    try:
        for step in sorted_steps:
            logger.info(
                "Run %s — step %d: %s",
                run_id,
                step.step_order,
                step.agent_type,
            )
            handler = get_handler(step.agent_type)
            result = await handler.execute(ctx, step.config)
            step_runs.append(
                StepRunRecord(
                    step_order=step.step_order,
                    agent_type=step.agent_type,
                    status="completed",
                    output=result.output,
                )
            )
    except Exception as e:
        logger.exception("Run %s failed at step %s", run_id, step.agent_type)
        step_runs.append(
            StepRunRecord(
                step_order=step.step_order,
                agent_type=step.agent_type,
                status="failed",
                error_message=str(e),
            )
        )
        return RunResult(
            run_id=run_id,
            upload_id=upload_id,
            task_description=task_description,
            status="failed",
            steps=step_runs,
            document_ids=document_ids,
            planned_steps=sorted_steps,
            workflow_id=workflow_id,
            error_message=str(e),
        )

    final_output = ctx.data.get("output")
    logger.info("Run %s completed — %d row(s)", run_id, len(ctx.data.get("rows", [])))

    return RunResult(
        run_id=run_id,
        upload_id=upload_id,
        task_description=task_description,
        status="completed",
        steps=step_runs,
        document_ids=document_ids,
        planned_steps=sorted_steps,
        workflow_id=workflow_id,
        result=final_output,
    )
