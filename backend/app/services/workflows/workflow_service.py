"""Workflow service — save and load workflow templates."""

import uuid
from dataclasses import replace
from typing import Optional

from app.agents.core.registry import is_valid_agent_type
from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult
from app.models.domain.workflow import WorkflowRecord, WorkflowSummary
from app.models.domain.user_template_version import TemplateVersionNotFoundError
from app.persistence.protocols import DataRepository
from app.persistence.serialization import planned_steps_from_json
from app.services.documents.upload_loader import UploadNotFoundError
from app.services.pipeline.runner import start_run
from app.services.templates.user_template_version_service import UserTemplateVersionService
from app.services.users.user_service import UserNotFoundError, UserService
from app.validation.task_input import sanitize_task_input


class WorkflowNotFoundError(Exception):
    pass


class RunNotFoundError(Exception):
    pass


class WorkflowService:
    def __init__(
        self,
        repo: DataRepository,
        users: UserService,
        versions: Optional[UserTemplateVersionService] = None,
    ) -> None:
        self._repo = repo
        self._users = users
        self._versions = versions

    def create_workflow(
        self,
        user_id: str,
        name: str,
        steps: list[PlannedStep],
        *,
        description: str = "",
        source: str = "planner",
        task_description: str = "",
        parent_template_id: Optional[str] = None,
        extraction_prompt: Optional[str] = None,
        current_template_version_id: Optional[str] = None,
    ) -> WorkflowRecord:
        self._users.require_user(user_id)

        if not steps and not current_template_version_id:
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
            task_description=sanitize_task_input(task_description),
            steps=sorted(steps, key=lambda s: s.step_order),
            parent_template_id=parent_template_id,
            current_template_version_id=current_template_version_id,
            extraction_prompt=extraction_prompt,
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
        if not run.planned_steps and not run.current_template_version_id:
            raise ValueError("This run has no saved plan to convert into a workflow")

        if self._versions is not None:
            planned_steps, prompt = self._versions.resolve_run_plan(run)
        else:
            planned_steps, prompt = run.planned_steps, run.extraction_prompt

        source = "chat_refined" if run.parent_run_id else "from_run"
        if run.template_id and not run.parent_run_id:
            source = f"template:{run.template_id}"

        workflow = self.create_workflow(
            user_id,
            name,
            planned_steps,
            description=description,
            source=source,
            task_description=run.task_description,
            parent_template_id=run.template_id,
            extraction_prompt=prompt,
        )

        if self._versions is not None and run.current_template_version_id:
            wf_version = self._versions.copy_run_version_to_workflow(
                run_version_id=run.current_template_version_id,
                workflow_id=workflow.workflow_id,
            )
            workflow.current_template_version_id = wf_version.version_id
            self._repo.save_workflow(workflow)

        run.workflow_id = workflow.workflow_id
        self._repo.save_run(run)
        return workflow

    def fetch_workflow(self, workflow_id: str) -> WorkflowRecord:
        workflow = self._repo.get_workflow(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")
        if self._versions is not None:
            return self._versions.hydrate_workflow(workflow)
        return workflow

    def fetch_all_workflows(self, user_id: Optional[str] = None) -> list[WorkflowSummary]:
        if user_id is not None:
            self._users.require_user(user_id)
        summaries = self._repo.list_workflows(user_id=user_id)
        return [self._enrich_summary_step_count(summary) for summary in summaries]

    def fetch_workflows_for_user(self, user_id: str) -> list[WorkflowSummary]:
        self._users.require_user(user_id)
        return self.fetch_all_workflows(user_id=user_id)

    def current_version_number(self, workflow: WorkflowRecord) -> Optional[int]:
        if not workflow.current_template_version_id or self._versions is None:
            return None
        items = self._versions.list_workflow_versions(
            workflow.workflow_id, workflow.current_template_version_id
        )
        for item in items:
            if item["is_current"]:
                return int(item["version_number"])
        return None

    def revert_to_version(self, workflow_id: str, version_id: str) -> WorkflowRecord:
        workflow = self._repo.get_workflow(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")
        if self._versions is None:
            raise ValueError("Version service not configured")

        try:
            branched = self._versions.branch_from_version(
                source_version_id=version_id,
                scope_type="workflow",
                scope_id=workflow_id,
                refine_summary="Branched from earlier version",
            )
            payload = self._versions.get_version_payload(branched.version_id)
        except TemplateVersionNotFoundError as exc:
            raise TemplateVersionNotFoundError(str(exc)) from exc

        workflow.current_template_version_id = branched.version_id
        workflow.extraction_prompt = payload.extraction_prompt
        workflow.steps = planned_steps_from_json(payload.planned_steps)
        self._repo.save_workflow(workflow)
        return self._versions.hydrate_workflow(workflow)

    async def start_workflow_run(self, workflow_id: str, upload_id: str) -> RunResult:
        workflow = self.fetch_workflow(workflow_id)
        steps, prompt, version_id = self.resolve_workflow_plan(workflow)
        run = await start_run(
            upload_id,
            steps,
            workflow.task_description,
            workflow_id=workflow.workflow_id,
            template_id=workflow.parent_template_id,
            extraction_prompt=prompt,
            current_template_version_id=version_id,
        )
        if self._versions is not None and version_id:
            run = self._versions.copy_workflow_version_to_run(
                workflow_version_id=version_id,
                run=run,
                template_id=workflow.parent_template_id,
            )
        return run

    def _enrich_summary_step_count(self, summary: WorkflowSummary) -> WorkflowSummary:
        if summary.step_count > 0 or self._versions is None:
            return summary
        workflow = self._repo.get_workflow(summary.workflow_id)
        if workflow is None or not workflow.current_template_version_id:
            return summary
        steps, _ = self._versions.resolve_workflow_plan(workflow)
        return replace(summary, step_count=len(steps))

    def fetch_runs_for_workflow(self, workflow_id: str) -> list[RunResult]:
        self.fetch_workflow(workflow_id)
        return self._repo.list_runs_by_workflow(workflow_id)

    def resolve_workflow_plan(self, workflow: WorkflowRecord) -> tuple[list[PlannedStep], str, Optional[str]]:
        if self._versions is not None:
            steps, prompt = self._versions.resolve_workflow_plan(workflow)
            return steps, prompt, workflow.current_template_version_id
        return workflow.steps, workflow.extraction_prompt or "", workflow.current_template_version_id

    def update_from_run(
        self,
        workflow_id: str,
        run_id: str,
        *,
        version_name: str = "",
        description: str = "",
    ) -> WorkflowRecord:
        """Update a workflow from a refined run — creates a new version."""
        workflow = self._repo.get_workflow(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")

        run = self._repo.get_run(run_id)
        if run is None:
            raise RunNotFoundError(f"Run not found: {run_id}")
        if run.status not in ("completed", "failed"):
            raise ValueError("Cannot update from a run that is still in progress")

        if self._versions is None:
            raise ValueError("Version service not configured")

        planned_steps, prompt = self._versions.resolve_run_plan(run)
        template_id = run.template_id or workflow.parent_template_id or "custom"
        summary = version_name.strip() or "Updated from run"

        wf_version = self._versions.create_workflow_version(
            scope_id=workflow_id,
            template_id=template_id,
            planned_steps=planned_steps,
            extraction_prompt=prompt,
            refine_summary=summary,
            parent_version_id=workflow.current_template_version_id,
            user_message=description,
        )

        workflow.current_template_version_id = wf_version.version_id
        workflow.extraction_prompt = prompt
        workflow.steps = planned_steps
        self._repo.save_workflow(workflow)
        return self._versions.hydrate_workflow(workflow)

    def update_settings(
        self,
        workflow_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        default_email: Optional[str] = None,
        default_sheets_url: Optional[str] = None,
    ) -> WorkflowRecord:
        """Update workflow metadata and delivery defaults."""
        workflow = self._repo.get_workflow(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")

        if name is not None:
            workflow.name = name.strip()
        if description is not None:
            workflow.description = description.strip()
        if default_email is not None:
            workflow.default_email = default_email.strip() or None
        if default_sheets_url is not None:
            workflow.default_sheets_url = default_sheets_url.strip() or None

        self._repo.save_workflow(workflow)
        if self._versions is not None:
            return self._versions.hydrate_workflow(workflow)
        return workflow

    def delete_workflow(self, workflow_id: str) -> None:
        """Permanently delete a workflow and its versioned template data."""
        workflow = self._repo.get_workflow(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(f"Workflow not found: {workflow_id}")

        if self._versions is not None:
            self._versions.delete_workflow_versions(workflow_id)

        self._repo.delete_workflow(workflow_id)
