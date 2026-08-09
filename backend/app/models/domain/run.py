"""Workflow execution domain models."""

from dataclasses import dataclass, field
from typing import Any, Optional

from app.models.domain.pipeline import PlannedStep


@dataclass
class StepRunRecord:
    step_order: int
    agent_type: str
    status: str  # queued | running | completed | failed | skipped
    output: dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class RunResult:
    run_id: str
    upload_id: str
    task_description: str
    status: str  # running | completed | failed
    steps: list[StepRunRecord]
    document_ids: list[str] = field(default_factory=list)
    planned_steps: list[PlannedStep] = field(default_factory=list)
    workflow_id: Optional[str] = None
    parent_run_id: Optional[str] = None
    template_id: Optional[str] = None
    current_template_version_id: Optional[str] = None
    extraction_prompt: Optional[str] = None
    cached_documents: Optional[list[dict[str, Any]]] = None
    refine_summary: Optional[str] = None
    result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None
    user_id: Optional[str] = None
