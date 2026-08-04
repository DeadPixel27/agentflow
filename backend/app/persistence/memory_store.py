"""In-memory persistence — used when Supabase is not configured."""

from typing import Optional

from app.models.domain.user import UserRecord
from app.models.domain.workflow import WorkflowRecord, WorkflowSummary
from app.models.domain.run import RunResult

_users: dict[str, UserRecord] = {}
_runs: dict[str, RunResult] = {}
_workflows: dict[str, WorkflowRecord] = {}


def save_user(user: UserRecord) -> None:
    _users[user.user_id] = user


def get_user(user_id: str) -> Optional[UserRecord]:
    return _users.get(user_id)


def list_users() -> list[UserRecord]:
    return list(_users.values())


def save_run(run: RunResult) -> None:
    _runs[run.run_id] = run


def get_run(run_id: str) -> Optional[RunResult]:
    return _runs.get(run_id)


def list_runs_by_workflow(workflow_id: str) -> list[RunResult]:
    runs = [run for run in _runs.values() if run.workflow_id == workflow_id]
    return sorted(runs, key=lambda run: run.run_id, reverse=True)


def save_workflow(workflow: WorkflowRecord) -> None:
    _workflows[workflow.workflow_id] = workflow


def get_workflow(workflow_id: str) -> Optional[WorkflowRecord]:
    return _workflows.get(workflow_id)


def list_workflows(user_id: Optional[str] = None) -> list[WorkflowSummary]:
    workflows = _workflows.values()
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
