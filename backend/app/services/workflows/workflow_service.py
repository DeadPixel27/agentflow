"""Workflow service — save and load workflow templates."""

import uuid
from typing import Optional

from app.agents.core.registry import is_valid_agent_type
from app.models.domain.pipeline import PlannedStep
from app.models.domain.workflow import WorkflowRecord
from app.persistence.store import get_run, get_workflow, list_runs_by_workflow, list_workflows, save_run, save_workflow
from app.services.users.user_service import UserNotFoundError, require_user


class WorkflowNotFoundError(Exception):
    pass


class RunNotFoundError(Exception):
    pass


def create_workflow(
    user_id: str,
    name: str,
    steps: list[PlannedStep],
    *,
    description: str = "",
    source: str = "planner",
    task_description: str = "",
) -> WorkflowRecord:
    require_user(user_id)

    if not steps:
        raise ValueError("At least one step is required")

    for step in steps:
        if not is_valid_agent_type(step.agent_type):
            raise ValueError(f"Unknown agent_type: {step.agent_type}")

    workflow = WorkflowRecord(
        workflow_id=str(uuid.uuid4()),
        user_id=user_id,
        name=name.strip(),
        description=description.strip(),
        source=source,
        task_description=task_description.strip(),
        steps=sorted(steps, key=lambda s: s.step_order),
    )
    save_workflow(workflow)
    return workflow


def create_workflow_from_run(
    user_id: str,
    run_id: str,
    name: str,
    *,
    description: str = "",
) -> WorkflowRecord:
    """Save the plan that was used for a run as a reusable workflow."""
    run = get_run(run_id)
    if run is None:
        raise RunNotFoundError(f"Run not found: {run_id}")
    if not run.planned_steps:
        raise ValueError("This run has no saved plan to convert into a workflow")

    workflow = create_workflow(
        user_id,
        name,
        run.planned_steps,
        description=description,
        source="from_run",
        task_description=run.task_description,
    )

    run.workflow_id = workflow.workflow_id
    save_run(run)
    return workflow


def fetch_workflow(workflow_id: str) -> WorkflowRecord:
    workflow = get_workflow(workflow_id)
    if workflow is None:
        raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")
    return workflow


def fetch_all_workflows(user_id: Optional[str] = None):
    if user_id is not None:
        require_user(user_id)
    return list_workflows(user_id=user_id)


def fetch_workflows_for_user(user_id: str):
    require_user(user_id)
    return list_workflows(user_id=user_id)


def fetch_runs_for_workflow(workflow_id: str):
    fetch_workflow(workflow_id)
    return list_runs_by_workflow(workflow_id)
