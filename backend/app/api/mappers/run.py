"""Map domain models to API responses."""

from app.models.api.pipeline import PlannedStepResponse
from app.models.api.runs import RunResponse, StepRunResponse
from app.models.domain.run import RunResult


def to_run_response(run: RunResult) -> RunResponse:
    return RunResponse(
        run_id=run.run_id,
        upload_id=run.upload_id,
        task_description=run.task_description,
        status=run.status,
        document_ids=run.document_ids,
        workflow_id=run.workflow_id,
        parent_run_id=run.parent_run_id,
        template_id=run.template_id,
        current_template_version_id=run.current_template_version_id,
        extraction_prompt=run.extraction_prompt,
        refine_summary=run.refine_summary,
        planned_steps=[
            PlannedStepResponse(
                step_order=step.step_order,
                agent_type=step.agent_type,
                config=step.config,
                reason=step.reason,
            )
            for step in run.planned_steps
        ],
        steps=[
            StepRunResponse(
                step_order=step.step_order,
                agent_type=step.agent_type,
                status=step.status,
                output=step.output,
                error_message=step.error_message,
            )
            for step in run.steps
        ],
        result=run.result,
        error_message=run.error_message,
    )
