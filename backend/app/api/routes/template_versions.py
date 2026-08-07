"""Template version routes — list, preview, and branch from versions."""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.dependencies import VersionServiceDep, WorkflowServiceDep
from app.api.mappers.template_version import to_template_version_detail
from app.models.api.template_versions import (
    RevertRunResponse,
    RevertVersionRequest,
    RevertWorkflowResponse,
    TemplateVersionDetailResponse,
    TemplateVersionSummaryResponse,
)
from app.models.domain.user_template_version import (
    RunNotBranchableError,
    RunNotFoundForVersionsError,
    TemplateVersionNotFoundError,
)
from app.services.documents.upload_loader import UploadNotFoundError
from app.services.pipeline.runner import execute_run
from app.services.workflows.workflow_service import WorkflowNotFoundError

router = APIRouter(tags=["template-versions"])


def _to_summary(item: dict) -> TemplateVersionSummaryResponse:
    return TemplateVersionSummaryResponse(**item)


@router.get(
    "/api/runs/{run_id}/template-versions",
    response_model=list[TemplateVersionSummaryResponse],
)
async def list_run_template_versions(
    run_id: str,
    versions: VersionServiceDep,
) -> list[TemplateVersionSummaryResponse]:
    try:
        items = versions.list_run_versions_for_run(run_id)
    except RunNotFoundForVersionsError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [_to_summary(item) for item in items]


@router.get(
    "/api/runs/{run_id}/template-versions/{version_id}",
    response_model=TemplateVersionDetailResponse,
)
async def get_run_template_version(
    run_id: str,
    version_id: str,
    versions: VersionServiceDep,
) -> TemplateVersionDetailResponse:
    try:
        detail = versions.build_run_version_detail(run_id, version_id)
    except RunNotFoundForVersionsError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TemplateVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return to_template_version_detail(
        detail.payload,
        version_number=detail.version_number,
        is_current=detail.is_current,
        steps=detail.steps,
    )


@router.post("/api/runs/{run_id}/revert", response_model=RevertRunResponse)
async def revert_run_to_version(
    run_id: str,
    body: RevertVersionRequest,
    background_tasks: BackgroundTasks,
    versions: VersionServiceDep,
) -> RevertRunResponse:
    """Branch from an earlier template version and start a new child run."""
    try:
        child = await versions.branch_run_from_version(run_id, body.version_id)
    except RunNotFoundForVersionsError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunNotBranchableError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except TemplateVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (UploadNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(execute_run, child.run_id)
    return RevertRunResponse(run_id=child.run_id)


@router.get(
    "/api/workflows/{workflow_id}/template-versions",
    response_model=list[TemplateVersionSummaryResponse],
)
async def list_workflow_template_versions(
    workflow_id: str,
    workflows: WorkflowServiceDep,
    versions: VersionServiceDep,
) -> list[TemplateVersionSummaryResponse]:
    try:
        workflow = workflows.fetch_workflow(workflow_id)
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    items = versions.list_workflow_versions(
        workflow_id, workflow.current_template_version_id
    )
    return [_to_summary(item) for item in items]


@router.get(
    "/api/workflows/{workflow_id}/template-versions/{version_id}",
    response_model=TemplateVersionDetailResponse,
)
async def get_workflow_template_version(
    workflow_id: str,
    version_id: str,
    workflows: WorkflowServiceDep,
    versions: VersionServiceDep,
) -> TemplateVersionDetailResponse:
    try:
        workflow = workflows.fetch_workflow(workflow_id)
        detail = versions.build_workflow_version_detail(
            workflow_id, version_id, workflow.current_template_version_id
        )
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TemplateVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return to_template_version_detail(
        detail.payload,
        version_number=detail.version_number,
        is_current=detail.is_current,
        steps=detail.steps,
    )


@router.post(
    "/api/workflows/{workflow_id}/revert",
    response_model=RevertWorkflowResponse,
)
async def revert_workflow_to_version(
    workflow_id: str,
    body: RevertVersionRequest,
    workflows: WorkflowServiceDep,
) -> RevertWorkflowResponse:
    """Branch workflow template from an earlier version (non-destructive)."""
    try:
        workflow = workflows.revert_to_version(workflow_id, body.version_id)
    except WorkflowNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TemplateVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return RevertWorkflowResponse(
        current_template_version_id=workflow.current_template_version_id or body.version_id
    )
