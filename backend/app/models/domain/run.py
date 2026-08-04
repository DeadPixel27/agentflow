"""Workflow execution domain models."""

from dataclasses import dataclass, field
from typing import Any, Optional

from app.models.domain.pipeline import PlannedStep


@dataclass
class StepRunRecord:
    step_order: int
    agent_type: str
    status: str  # completed | failed
    output: dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class RunResult:
    run_id: str
    upload_id: str
    task_description: str
    status: str  # completed | failed
    steps: list[StepRunRecord]
    document_ids: list[str] = field(default_factory=list)
    planned_steps: list[PlannedStep] = field(default_factory=list)
    workflow_id: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
