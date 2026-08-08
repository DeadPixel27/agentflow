"""Saved workflow domain models."""

from dataclasses import dataclass
from typing import Optional

from app.models.domain.pipeline import PlannedStep


@dataclass
class WorkflowRecord:
    workflow_id: str
    user_id: str
    name: str
    description: str
    source: str
    task_description: str
    steps: list[PlannedStep]
    parent_template_id: Optional[str] = None
    current_template_version_id: Optional[str] = None
    extraction_prompt: Optional[str] = None
    created_at: Optional[str] = None
    default_email: Optional[str] = None
    default_sheets_url: Optional[str] = None


@dataclass
class WorkflowSummary:
    workflow_id: str
    user_id: str
    name: str
    description: str
    source: str
    step_count: int
    created_at: Optional[str] = None
