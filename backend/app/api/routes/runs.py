"""
Runs Route — execute pipeline plans and fetch run results.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.api.dependencies import RefineServiceDep, RepoDep, TemplateServiceDep, VersionServiceDep
from app.api.mappers.planned_step import to_planned_steps
from app.api.mappers.run import to_run_response
from app.config import settings
from app.models.api.runs import (
    RunAdhocRequest,
    RefinePlanRequest,
    RefinePlanResponse,
    RunRefineRequest,
    RunRefineResponse,
    RunRequest,
    RunResponse,
    RunTemplateRequest,
)
from app.services.pipeline.refine_service import (
    RunNotFoundError,
    RunNotRefinableError,
)
from app.services.pipeline.pipeline_refiner import RefinerError
from app.rate_limit import limiter
from app.models.domain.template import TemplateNotFoundError
from app.services.documents.upload_loader import UploadNotFoundError
from app.services.pipeline.planner import create_plan
from app.services.pipeline.runner import execute_run, start_run

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _schedule_run(background_tasks: BackgroundTasks, run_id: str) -> None:
    background_tasks.add_task(execute_run, run_id)


@router.post("/adhoc", response_model=RunResponse)
@limiter.limit(settings.rate_limit_runs_adhoc)
async def run_adhoc(
    request: Request,
    body: RunAdhocRequest,
    background_tasks: BackgroundTasks,
) -> RunResponse:
    """Plan a pipeline and start execution. Poll GET /api/runs/{id} for progress."""
    try:
        plan = await create_plan(body.upload_id, body.task_description)
        run = await start_run(
            body.upload_id,
            plan.steps,
            plan.task_description,
        )
    except UploadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    _schedule_run(background_tasks, run.run_id)
    return to_run_response(run)


@router.post("/template", response_model=RunResponse)
@limiter.limit(settings.rate_limit_runs_adhoc)
async def run_template(
    request: Request,
    body: RunTemplateRequest,
    background_tasks: BackgroundTasks,
    template_service: TemplateServiceDep,
    versions: VersionServiceDep,
) -> RunResponse:
    """Run a pipeline from a template definition. Poll GET /api/runs/{id} for progress."""
    try:
        plan = await template_service.build_plan(body.template_id, body.upload_id)
        template = template_service.get_template(body.template_id)
        run = await start_run(
            body.upload_id,
            plan.steps,
            plan.task_description,
            template_id=template.template_id,
            extraction_prompt=template.extraction_instructions,
        )
        run = versions.attach_initial_run_version(
            run,
            template_id=template.template_id,
            planned_steps=run.planned_steps,
            extraction_prompt=template.extraction_instructions,
        )
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UploadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    _schedule_run(background_tasks, run.run_id)
    return to_run_response(run)


@router.post("", response_model=RunResponse)
async def run_pipeline_steps(
    body: RunRequest,
    background_tasks: BackgroundTasks,
) -> RunResponse:
    """Run an explicit plan. Poll GET /api/runs/{id} for progress."""
    try:
        steps = to_planned_steps(body.steps)
        run = await start_run(
            body.upload_id,
            steps,
            body.task_description,
        )
    except UploadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    _schedule_run(background_tasks, run.run_id)
    return to_run_response(run)


@router.post("/{run_id}/refine/plan", response_model=RefinePlanResponse)
async def refine_plan(
    run_id: str,
    body: RefinePlanRequest,
    repo: RepoDep,
) -> RefinePlanResponse:
    """
    Plan Mode: clarify user intent with a cheap/fast model before re-running.
    Call this for each chat message. When response.ready is true,
    call POST /refine with the accumulated_instruction as the message.
    """
    from app.services.pipeline.refine_chat import plan_refinement

    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    rows = (run.result or {}).get("rows", [])
    field_names = list(rows[0].keys()) if rows else []
    skip = {"document_id", "flags"}
    field_names = [f for f in field_names if f not in skip]

    chat_history = [{"role": m.role, "content": m.content} for m in body.chat_history]

    try:
        result = await plan_refinement(
            message=body.message,
            chat_history=chat_history,
            field_names=field_names,
            sample_rows=rows[:2],
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Plan mode failed: {e}") from e

    return RefinePlanResponse(
        ready=result["ready"],
        message=result["message"],
        planned_changes=result["planned_changes"],
        accumulated_instruction=result["accumulated_instruction"],
    )


@router.post("/{run_id}/refine", response_model=RunRefineResponse)
@limiter.limit(settings.rate_limit_runs_adhoc)
async def refine_run(
    request: Request,
    run_id: str,
    body: RunRefineRequest,
    background_tasks: BackgroundTasks,
    refine_service: RefineServiceDep,
) -> RunRefineResponse:
    """Refine a completed run's pipeline via chat and start a child run."""
    try:
        run, summary = await refine_service.refine_and_start(run_id, body.message)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RunNotRefinableError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RefinerError as e:
        raise HTTPException(status_code=502, detail=str(e))

    _schedule_run(background_tasks, run.run_id)
    return RunRefineResponse(run=to_run_response(run), refine_summary=summary)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run_status(
    run_id: str,
    repo: RepoDep,
    versions: VersionServiceDep,
) -> RunResponse:
    """Fetch a run — poll while status is 'running'."""
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return to_run_response(versions.hydrate_run(run))
