"""
Runs Route — execute pipeline plans and fetch run results.
"""

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.api.dependencies import RepoDep
from app.api.mappers.run import to_run_response
from app.models.api.runs import RunAdhocRequest, RunRequest, RunResponse
from app.models.domain.pipeline import PlannedStep
from app.services.documents.upload_loader import UploadNotFoundError
from app.services.pipeline.planner import create_plan
from app.services.pipeline.runner import execute_run, start_run

router = APIRouter(prefix="/api/runs", tags=["runs"])


def _to_planned_steps(steps: list) -> list[PlannedStep]:
    return [
        PlannedStep(
            step_order=step.step_order,
            agent_type=step.agent_type,
            config=step.config,
            reason=step.reason,
        )
        for step in steps
    ]


def _schedule_run(background_tasks: BackgroundTasks, run_id: str) -> None:
    background_tasks.add_task(execute_run, run_id)


@router.post("/adhoc", response_model=RunResponse)
async def run_adhoc(
    body: RunAdhocRequest,
    background_tasks: BackgroundTasks,
) -> RunResponse:
    """Plan a pipeline and start execution. Poll GET /api/runs/{id} for progress."""
    try:
        plan = await create_plan(body.upload_id, body.task_description)
        run = await start_run(
            body.upload_id,
            plan.steps,
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


@router.post("", response_model=RunResponse)
async def run_pipeline_steps(
    body: RunRequest,
    background_tasks: BackgroundTasks,
) -> RunResponse:
    """Run an explicit plan. Poll GET /api/runs/{id} for progress."""
    try:
        steps = _to_planned_steps(body.steps)
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


@router.get("/{run_id}", response_model=RunResponse)
async def get_run_status(run_id: str, repo: RepoDep) -> RunResponse:
    """Fetch a run — poll while status is 'running'."""
    run = repo.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return to_run_response(run)
