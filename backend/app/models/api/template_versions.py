from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.api.pipeline import PlannedStepResponse


class TemplateVersionSummaryResponse(BaseModel):
    version_id: str
    version_number: int
    refine_summary: str
    parent_version_id: Optional[str] = None
    is_current: bool = False
    created_at: Optional[str] = None
    template_id: str


class TemplateVersionDetailResponse(TemplateVersionSummaryResponse):
    extraction_prompt: str
    planned_steps: list[PlannedStepResponse] = Field(default_factory=list)
    user_message: Optional[str] = None


class RevertVersionRequest(BaseModel):
    version_id: str = Field(min_length=1)


class RevertRunResponse(BaseModel):
    run_id: str


class RevertWorkflowResponse(BaseModel):
    current_template_version_id: str
