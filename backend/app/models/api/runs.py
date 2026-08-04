from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.api.pipeline import PlannedStepResponse


class PlannedStepInput(BaseModel):
    step_order: int
    agent_type: str
    config: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class RunRequest(BaseModel):
    upload_id: str
    steps: list[PlannedStepInput] = Field(min_length=1)
    task_description: str = ""


class RunAdhocRequest(BaseModel):
    upload_id: str
    task_description: str = Field(min_length=1)


class StepRunResponse(BaseModel):
    step_order: int
    agent_type: str
    status: str
    output: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class RunResponse(BaseModel):
    run_id: str
    upload_id: str
    task_description: str
    status: str
    document_ids: list[str] = Field(default_factory=list)
    steps: list[StepRunResponse]
    planned_steps: list[PlannedStepResponse] = Field(default_factory=list)
    workflow_id: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
