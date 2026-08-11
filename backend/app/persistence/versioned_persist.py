"""Helpers for persisting runs/workflows with versioned template payloads."""

from dataclasses import replace

from app.models.domain.run import RunResult
from app.models.domain.workflow import WorkflowRecord


def strip_run_for_persist(run: RunResult) -> RunResult:
    """Omit template payload from DB when a storage version pointer exists."""
    if not run.current_template_version_id:
        return run
    return replace(run, planned_steps=[], extraction_prompt=None)


def strip_workflow_for_persist(workflow: WorkflowRecord) -> WorkflowRecord:
    """Omit template payload from DB when a storage version pointer exists."""
    if not workflow.current_template_version_id:
        return workflow
    return replace(workflow, steps=[], extraction_prompt=None)
