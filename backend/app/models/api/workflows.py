from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.api.runs import PlannedStepInput


class WorkflowCreateRequest(BaseModel):
    user_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    steps: list[PlannedStepInput] = Field(min_length=1)
    description: str = ""
    source: str = "planner"
    task_description: str = ""


class WorkflowStepResponse(BaseModel):
    step_order: int
    agent_type: str
    config: dict[str, Any]
    reason: str


class WorkflowResponse(BaseModel):
    workflow_id: str
    user_id: str
    name: str
    description: str
    source: str
    task_description: str
    parent_template_id: Optional[str] = None
    current_template_version_id: Optional[str] = None
    current_version_number: Optional[int] = None
    extraction_prompt: Optional[str] = None
    steps: list[WorkflowStepResponse]
    created_at: Optional[str] = None
    default_email: Optional[str] = None
    default_sheets_url: Optional[str] = None
    default_sheet_name: Optional[str] = None


class WorkflowSummaryResponse(BaseModel):
    workflow_id: str
    user_id: str
    name: str
    description: str
    source: str
    step_count: int
    created_at: Optional[str] = None


class WorkflowRunRequest(BaseModel):
    upload_id: str


class WorkflowFromRunRequest(BaseModel):
    """Save the plan from a completed run as a reusable workflow."""

    user_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = ""


class WorkflowUpdateFromRunRequest(BaseModel):
    """Update a workflow's template from a refined run."""

    run_id: str = Field(min_length=1, validation_alias="from_run_id")
    version_name: str = ""
    description: str = ""

    model_config = {"populate_by_name": True}


class WorkflowSettingsUpdateRequest(BaseModel):
    """Update workflow settings (name, description, delivery defaults)."""

    name: Optional[str] = None
    description: Optional[str] = None
    default_email: Optional[str] = None
    default_sheets_url: Optional[str] = None
    default_sheet_name: Optional[str] = None
