"""Workflow service — save and load workflow templates."""

import uuid
from typing import Optional

from app.agents.core.registry import is_valid_agent_type
from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult
from app.models.domain.workflow import WorkflowRecord
from app.persistence.protocols import DataRepository
from app.services.users.user_service import UserNotFoundError, UserService


class WorkflowNotFoundError(Exception):
    pass


class RunNotFoundError(Exception):
    pass


class WorkflowService:
    def __init__(self, repo: DataRepository, users: UserService) -> None:
        self._repo = repo
        self._users = users

    def create_workflow(
        self,
        user_id: str,
        name: str,
        steps: list[PlannedStep],
        *,
        description: str = "",
        source: str = "planner",
        task_description: str = "",
    ) -> WorkflowRecord:
        self._users.require_user(user_id)

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
        self._repo.save_workflow(workflow)
        return workflow

    def create_workflow_from_run(
        self,
        user_id: str,
        run_id: str,
        name: str,
        *,
        description: str = "",
    ) -> WorkflowRecord:
        """Save the plan that was used for a run as a reusable workflow."""
        run = self._repo.get_run(run_id)
        if run is None:
            raise RunNotFoundError(f"Run not found: {run_id}")
        if not run.planned_steps:
            raise ValueError("This run has no saved plan to convert into a workflow")

        workflow = self.create_workflow(
            user_id,
            name,
            run.planned_steps,
            description=description,
            source="from_run",
            task_description=run.task_description,
        )

        run.workflow_id = workflow.workflow_id
        self._repo.save_run(run)
        return workflow

    def fetch_workflow(self, workflow_id: str) -> WorkflowRecord:
        workflow = self._repo.get_workflow(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")
        return workflow

    def fetch_all_workflows(self, user_id: Optional[str] = None):
        if user_id is not None:
            self._users.require_user(user_id)
        return self._repo.list_workflows(user_id=user_id)

    def fetch_workflows_for_user(self, user_id: str):
        self._users.require_user(user_id)
        return self._repo.list_workflows(user_id=user_id)

    def fetch_runs_for_workflow(self, workflow_id: str) -> list[RunResult]:
        self.fetch_workflow(workflow_id)
        return self._repo.list_runs_by_workflow(workflow_id)
