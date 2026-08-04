"""
Runs Route — execute pipeline plans and fetch run results.
"""

from fastapi import APIRouter, HTTPException

from app.api.mappers.run import to_run_response
from app.models.api.runs import RunAdhocRequest, RunRequest, RunResponse
from app.models.domain.pipeline import PlannedStep
from app.persistence.store import get_run, save_run
from app.services.pipeline.planner import create_plan
from app.services.pipeline.runner import run_pipeline
from app.services.documents.upload_loader import UploadNotFoundError

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


@router.post("/adhoc", response_model=RunResponse)
async def run_adhoc(body: RunAdhocRequest) -> RunResponse:
    """Plan and run in one call. Response includes planned_steps for saving."""
    try:
        plan = await create_plan(body.upload_id, body.task_description)
        run = await run_pipeline(
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

    save_run(run)
    return to_run_response(run)


@router.post("", response_model=RunResponse)
async def run_pipeline_steps(body: RunRequest) -> RunResponse:
    """Run an explicit plan (e.g. output from POST /api/pipeline/create)."""
    try:
        steps = _to_planned_steps(body.steps)
        run = await run_pipeline(
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

    save_run(run)
    return to_run_response(run)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run_status(run_id: str) -> RunResponse:
    """Fetch a completed or failed run by ID."""
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return to_run_response(run)
