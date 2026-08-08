"""
Workflows Route — save, list, and run reusable workflow templates.
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.api.dependencies import WorkflowServiceDep
from app.api.mappers.planned_step import to_planned_steps
from app.api.mappers.run import to_run_response
from app.models.api.runs import RunResponse
from app.models.api.workflows import (
    WorkflowCreateRequest,
    WorkflowFromRunRequest,
    WorkflowResponse,
    WorkflowRunRequest,
    WorkflowSettingsUpdateRequest,
    WorkflowStepResponse,
    WorkflowSummaryResponse,
    WorkflowUpdateFromRunRequest,
)
from app.services.documents.upload_loader import UploadNotFoundError
from app.services.pipeline.runner import execute_run
from app.services.users.user_service import UserNotFoundError
from app.services.workflows.workflow_service import RunNotFoundError, WorkflowNotFoundError

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def _to_workflow_response(workflow, *, current_version_number: Optional[int] = None) -> WorkflowResponse:
    return WorkflowResponse(
        workflow_id=workflow.workflow_id,
        user_id=workflow.user_id,
        name=workflow.name,
        description=workflow.description,
        source=workflow.source,
        task_description=workflow.task_description,
        parent_template_id=workflow.parent_template_id,
        current_template_version_id=workflow.current_template_version_id,
        current_version_number=current_version_number,
        extraction_prompt=workflow.extraction_prompt,
        steps=[
            WorkflowStepResponse(
                step_order=step.step_order,
                agent_type=step.agent_type,
                config=step.config,
                reason=step.reason,
            )
            for step in workflow.steps
        ],
        created_at=workflow.created_at,
        default_email=workflow.default_email,
        default_sheets_url=workflow.default_sheets_url,
    )


@router.post("", response_model=WorkflowResponse)
async def save_workflow(
    body: WorkflowCreateRequest,
    workflows: WorkflowServiceDep,
) -> WorkflowResponse:
    """Save a plan as a reusable workflow template."""
    try:
        workflow = workflows.create_workflow(
            body.user_id,
            body.name,
            to_planned_steps(body.steps),
            description=body.description,
            source=body.source,
            task_description=body.task_description,
        )
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _to_workflow_response(workflow)


@router.post("/from-run/{run_id}", response_model=WorkflowResponse)
async def save_workflow_from_run(
    run_id: str,
    body: WorkflowFromRunRequest,
    workflows: WorkflowServiceDep,
) -> WorkflowResponse:
    """Save the plan from a prior run (e.g. after POST /api/runs/adhoc)."""
    try:
        workflow = workflows.create_workflow_from_run(
            body.user_id,
            run_id,
            body.name,
            description=body.description,
        )
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return _to_workflow_response(workflow)


@router.get("", response_model=list[WorkflowSummaryResponse])
async def list_workflows(
    workflows: WorkflowServiceDep,
    user_id: Optional[str] = Query(default=None, description="Filter by owner"),
) -> list[WorkflowSummaryResponse]:
    """List saved workflows, optionally filtered by user."""
    try:
        if user_id is not None:
            summaries = workflows.fetch_all_workflows(user_id=user_id)
        else:
            summaries = workflows.fetch_all_workflows()
    except UserNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return [
        WorkflowSummaryResponse(
            workflow_id=item.workflow_id,
            user_id=item.user_id,
            name=item.name,
            description=item.description,
            source=item.source,
            step_count=item.step_count,
            created_at=item.created_at,
        )
        for item in summaries
    ]


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    workflows: WorkflowServiceDep,
) -> WorkflowResponse:
    """Get a saved workflow with its steps."""
    try:
        workflow = workflows.fetch_workflow(workflow_id)
    except WorkflowNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return _to_workflow_response(
        workflow,
        current_version_number=workflows.current_version_number(workflow),
    )


@router.get("/{workflow_id}/runs", response_model=list[RunResponse])
async def list_workflow_runs(
    workflow_id: str,
    workflows: WorkflowServiceDep,
) -> list[RunResponse]:
    """List all runs executed with this workflow."""
    try:
        runs = workflows.fetch_runs_for_workflow(workflow_id)
    except WorkflowNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return [to_run_response(run) for run in runs]


@router.post("/{workflow_id}/runs", response_model=RunResponse)
async def run_saved_workflow(
    workflow_id: str,
    body: WorkflowRunRequest,
    background_tasks: BackgroundTasks,
    workflows: WorkflowServiceDep,
) -> RunResponse:
    """Run a saved workflow on a new upload. Poll GET /api/runs/{id} for progress."""
    try:
        run = await workflows.start_workflow_run(workflow_id, body.upload_id)
    except WorkflowNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UploadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    background_tasks.add_task(execute_run, run.run_id)
    return to_run_response(run)


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow_from_run(
    workflow_id: str,
    body: WorkflowUpdateFromRunRequest,
    workflows: WorkflowServiceDep,
) -> WorkflowResponse:
    """Update a workflow's template from a refined run (creates a new version)."""
    try:
        workflow = workflows.update_from_run(
            workflow_id,
            body.run_id,
            version_name=body.version_name,
            description=body.description,
        )
    except WorkflowNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return _to_workflow_response(
        workflow,
        current_version_number=workflows.current_version_number(workflow),
    )


@router.patch("/{workflow_id}/settings", response_model=WorkflowResponse)
@router.put("/{workflow_id}/settings", response_model=WorkflowResponse)
async def update_workflow_settings(
    workflow_id: str,
    body: WorkflowSettingsUpdateRequest,
    workflows: WorkflowServiceDep,
) -> WorkflowResponse:
    """Update workflow metadata and delivery defaults."""
    try:
        workflow = workflows.update_settings(
            workflow_id,
            name=body.name,
            description=body.description,
            default_email=body.default_email,
            default_sheets_url=body.default_sheets_url,
        )
    except WorkflowNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    return _to_workflow_response(
        workflow,
        current_version_number=workflows.current_version_number(workflow),
    )
