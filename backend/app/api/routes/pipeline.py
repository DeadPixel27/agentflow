"""
Pipeline Route — planner creates a step pipeline from task + upload.
"""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import CurrentUserDep
from app.config import settings
from app.models.api.pipeline import (
    PipelineCreateRequest,
    PipelineCreateResponse,
    PlannedStepResponse,
)
from app.services.pipeline.planner import create_plan
from app.services.documents.upload_loader import UploadNotFoundError

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/create", response_model=PipelineCreateResponse)
async def create_pipeline(
    body: PipelineCreateRequest,
    current_user: CurrentUserDep,
) -> PipelineCreateResponse:
    """
    Plan a document processing pipeline from a task description and upload.

    The planner inspects uploaded documents and returns an ordered list of
    agent steps (field extraction, rules, formatting, etc.).
    """
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
