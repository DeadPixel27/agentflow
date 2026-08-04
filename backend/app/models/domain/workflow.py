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
    created_at: Optional[str] = None


@dataclass
class WorkflowSummary:
    workflow_id: str
    user_id: str
    name: str
    description: str
    source: str
    step_count: int
    created_at: Optional[str] = None
