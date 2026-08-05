"""In-memory data repository — dev / tests when no database is configured."""

from typing import Optional

from app.models.domain.run import RunResult
from app.models.domain.user import UserRecord
from app.models.domain.workflow import WorkflowRecord, WorkflowSummary


class MemoryRepository:
    backend_name = "memory"

    def __init__(self) -> None:
        self._users: dict[str, UserRecord] = {}
        self._runs: dict[str, RunResult] = {}
        self._workflows: dict[str, WorkflowRecord] = {}

    def health_check(self) -> tuple[bool, str]:
        return True, "in_memory"

    def save_user(self, user: UserRecord) -> None:
        self._users[user.user_id] = user

    def get_user(self, user_id: str) -> Optional[UserRecord]:
        return self._users.get(user_id)

    def get_user_by_email(self, email: str) -> Optional[UserRecord]:
        normalized = email.strip().lower()
        for user in self._users.values():
            if user.email.strip().lower() == normalized:
                return user
        return None

    def list_users(self) -> list[UserRecord]:
        return list(self._users.values())

    def save_run(self, run: RunResult) -> None:
        self._runs[run.run_id] = run

    def get_run(self, run_id: str) -> Optional[RunResult]:
        return self._runs.get(run_id)

    def list_runs_by_workflow(self, workflow_id: str) -> list[RunResult]:
        runs = [run for run in self._runs.values() if run.workflow_id == workflow_id]
        return sorted(runs, key=lambda run: run.run_id, reverse=True)

    def save_workflow(self, workflow: WorkflowRecord) -> None:
        self._workflows[workflow.workflow_id] = workflow

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowRecord]:
        return self._workflows.get(workflow_id)

    def list_workflows(self, user_id: Optional[str] = None) -> list[WorkflowSummary]:
        workflows = self._workflows.values()
        if user_id is not None:
            workflows = [wf for wf in workflows if wf.user_id == user_id]

        return [
            WorkflowSummary(
                workflow_id=wf.workflow_id,
                user_id=wf.user_id,
                name=wf.name,
                description=wf.description,
                source=wf.source,
                step_count=len(wf.steps),
                created_at=wf.created_at,
            )
            for wf in workflows
        ]
