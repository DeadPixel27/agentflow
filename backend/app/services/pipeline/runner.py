"""
Workflow runner — executes an ordered list of steps against an upload.

Runs are started with status "running" and step rows "queued", then executed
in a background task with progress persisted after each step for polling.
"""

import logging
import uuid
from dataclasses import replace
from typing import Optional

import app.agents.handlers  # noqa: F401 — register agents
from app.agents.core.context import WorkflowContext, documents_to_dicts
from app.agents.core.registry import get_handler
from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult, StepRunRecord
from app.persistence import get_run, save_run
from app.services.documents.upload_loader import load_upload_documents

logger = logging.getLogger("runner")


def _sorted_steps(steps: list[PlannedStep]) -> list[PlannedStep]:
    return sorted(steps, key=lambda s: s.step_order)


async def start_run(
    upload_id: str,
    steps: list[PlannedStep],
    task_description: str = "",
    workflow_id: Optional[str] = None,
) -> RunResult:
    """Create a run record in 'running' state with queued steps."""
    documents = await load_upload_documents(upload_id)
    if not documents:
        raise ValueError(f"No documents found for upload {upload_id}")

    document_ids = [doc.document_id for doc in documents]
    planned = _sorted_steps(steps)
    run_id = str(uuid.uuid4())

    run = RunResult(
        run_id=run_id,
        upload_id=upload_id,
        task_description=task_description,
        status="running",
        steps=[
            StepRunRecord(
                step_order=step.step_order,
                agent_type=step.agent_type,
                status="queued",
            )
            for step in planned
        ],
        document_ids=document_ids,
        planned_steps=planned,
        workflow_id=workflow_id,
    )
    save_run(run)
    logger.info(
        "Run %s started — upload_id=%s, %d step(s)",
        run_id,
        upload_id,
        len(planned),
    )
    return run


async def execute_run(run_id: str) -> None:
    """Execute a started run, saving progress after each step."""
    run = get_run(run_id)
    if run is None:
        logger.error("Run %s not found for execution", run_id)
        return
    if run.status != "running":
        logger.warning("Run %s is not running (status=%s)", run_id, run.status)
        return

    documents = await load_upload_documents(run.upload_id)
    ctx = WorkflowContext(
        upload_id=run.upload_id,
        task_description=run.task_description,
        data={"documents": documents_to_dicts(documents)},
    )

    step_runs = list(run.steps)
    planned = _sorted_steps(run.planned_steps)

    try:
        for index, step in enumerate(planned):
            logger.info(
                "Run %s — step %d: %s",
                run_id,
                step.step_order,
                step.agent_type,
            )
            step_runs[index] = replace(
                step_runs[index],
                status="running",
                error_message=None,
            )
            save_run(replace(run, steps=step_runs))

            handler = get_handler(step.agent_type)
            result = await handler.execute(ctx, step.config)
            step_runs[index] = replace(
                step_runs[index],
                status="completed",
                output=result.output,
            )
            save_run(replace(run, steps=step_runs))

    except Exception as e:
        logger.exception("Run %s failed at step %s", run_id, step.agent_type)
        step_runs[index] = replace(
            step_runs[index],
            status="failed",
            error_message=str(e),
        )
        save_run(
            replace(
                run,
                status="failed",
                steps=step_runs,
                error_message=str(e),
            )
        )
        return

    final_output = ctx.data.get("output")
    logger.info("Run %s completed — %d row(s)", run_id, len(ctx.data.get("rows", [])))
    save_run(
        replace(
            run,
            status="completed",
            steps=step_runs,
            result=final_output,
        )
    )


async def run_pipeline(
    upload_id: str,
    steps: list[PlannedStep],
    task_description: str = "",
    workflow_id: Optional[str] = None,
) -> RunResult:
    """Run synchronously (used in tests or when background execution is not needed)."""
    run = await start_run(upload_id, steps, task_description, workflow_id)
    await execute_run(run.run_id)
    finished = get_run(run.run_id)
    return finished if finished is not None else run
