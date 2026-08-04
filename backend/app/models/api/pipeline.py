from typing import Any

from pydantic import BaseModel, Field


class PipelineCreateRequest(BaseModel):
    upload_id: str
    task_description: str = Field(
        min_length=1,
        description=(
            "Plain-English task, e.g. "
            "'Extract vendor, amount, date. Flag over 50K. Give me CSV.'"
        ),
    )


class PlannedStepResponse(BaseModel):
    step_order: int
    agent_type: str
    config: dict[str, Any]
    reason: str


class PipelineCreateResponse(BaseModel):
    pipeline_id: str
    upload_id: str
    task_description: str
    steps: list[PlannedStepResponse]
    summary: str
    model: str
