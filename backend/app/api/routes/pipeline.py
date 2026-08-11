"""
Pipeline Route — planner creates a step pipeline from task + upload.
"""

from fastapi import APIRouter, HTTPException, Request

from app.api.dependencies import CurrentUserDep, RepoDep
from app.api.ownership import get_owned_upload
from app.config import settings
from app.models.api.pipeline import (
    PipelineCreateRequest,
    PipelineCreateResponse,
    PlannedStepResponse,
)
from app.rate_limit import limiter
from app.services.documents.upload_loader import UploadNotFoundError
from app.services.pipeline.planner import create_plan

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/create", response_model=PipelineCreateResponse)
@limiter.limit(settings.rate_limit_pipeline)
async def create_pipeline(
    request: Request,
    body: PipelineCreateRequest,
    repo: RepoDep,
    current_user: CurrentUserDep,
) -> PipelineCreateResponse:
    """
    Plan a document processing pipeline from a task description and upload.

    The planner inspects uploaded documents and returns an ordered list of
    agent steps (field extraction, rules, formatting, etc.).
    """
    get_owned_upload(repo, body.upload_id, current_user)
    try:
        plan = await create_plan(body.upload_id, body.task_description)
    except UploadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return PipelineCreateResponse(
        pipeline_id=plan.pipeline_id,
        upload_id=plan.upload_id,
        task_description=plan.task_description,
        steps=[
            PlannedStepResponse(
                step_order=step.step_order,
                agent_type=step.agent_type,
                config=step.config,
                reason=step.reason,
            )
            for step in plan.steps
        ],
        summary=plan.summary,
        model=settings.groq_model,
    )
