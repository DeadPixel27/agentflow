"""User template version service — object storage payloads + DB metadata."""

import logging
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult
from app.models.domain.workflow import WorkflowRecord
from app.models.domain.user_template_version import (
    RefinementEvent,
    RunNotBranchableError,
    RunNotFoundForVersionsError,
    TemplateVersionDetailView,
    TemplateVersionNotFoundError,
    UserTemplateVersionPayload,
    UserTemplateVersionRecord,
)
from app.persistence.protocols import DataRepository, UserTemplateStorageRepository
from app.persistence.serialization import planned_steps_from_json, planned_steps_to_json
from app.services.pipeline.extraction_prompt import (
    read_prompt_from_steps,
    resolve_run_extraction_prompt,
    sync_prompt_to_steps,
)

logger = logging.getLogger("user_template_versions")


def resolve_root_run_id(repo: DataRepository, run_id: str) -> str:
    """Walk parent_run_id chain to find the root run (version scope)."""
    current_id = run_id
    seen: set[str] = set()
    while True:
        if current_id in seen:
            break
        seen.add(current_id)
        run = repo.get_run(current_id)
        if run is None or not run.parent_run_id:
            return current_id
        current_id = run.parent_run_id
    return current_id


class UserTemplateVersionService:
    def __init__(
        self,
        repo: DataRepository,
        store: UserTemplateStorageRepository,
    ) -> None:
        self._repo = repo
        self._store = store

    def create_run_version(
        self,
        *,
        scope_id: str,
        template_id: str,
        planned_steps: list[PlannedStep],
        extraction_prompt: str,
        refine_summary: str = "Initial (from template)",
        parent_version_id: Optional[str] = None,
        user_message: Optional[str] = None,
    ) -> UserTemplateVersionRecord:
        return self._create_version(
            scope_type="run",
            scope_id=scope_id,
            template_id=template_id,
            planned_steps=planned_steps,
            extraction_prompt=extraction_prompt,
            refine_summary=refine_summary,
            parent_version_id=parent_version_id,
            user_message=user_message,
        )

    def create_workflow_version(
        self,
        *,
        scope_id: str,
        template_id: str,
        planned_steps: list[PlannedStep],
        extraction_prompt: str,
        refine_summary: str = "Initial (from run)",
        parent_version_id: Optional[str] = None,
        user_message: Optional[str] = None,
    ) -> UserTemplateVersionRecord:
        return self._create_version(
            scope_type="workflow",
            scope_id=scope_id,
            template_id=template_id,
            planned_steps=planned_steps,
            extraction_prompt=extraction_prompt,
            refine_summary=refine_summary,
            parent_version_id=parent_version_id,
            user_message=user_message,
        )

    def branch_from_version(
        self,
        *,
        source_version_id: str,
        scope_type: str,
        scope_id: str,
        refine_summary: str = "Branched from earlier version",
    ) -> UserTemplateVersionRecord:
        source = self.get_version_payload(source_version_id)
        return self._create_version(
            scope_type=scope_type,
            scope_id=scope_id,
            template_id=source.template_id,
            planned_steps=planned_steps_from_json(source.planned_steps),
            extraction_prompt=source.extraction_prompt,
            refine_summary=refine_summary,
            parent_version_id=source_version_id,
        )

    def copy_run_version_to_workflow(
        self,
        *,
        run_version_id: str,
        workflow_id: str,
        refine_summary: str = "Saved from run",
    ) -> UserTemplateVersionRecord:
        source = self.get_version_payload(run_version_id)
        return self.create_workflow_version(
            scope_id=workflow_id,
            template_id=source.template_id,
            planned_steps=planned_steps_from_json(source.planned_steps),
            extraction_prompt=source.extraction_prompt,
            refine_summary=refine_summary,
            parent_version_id=run_version_id,
        )

    def require_run(self, run_id: str) -> RunResult:
        run = self._repo.get_run(run_id)
        if run is None:
            raise RunNotFoundForVersionsError(f"Run not found: {run_id}")
        return run

    def list_run_versions_for_run(self, run_id: str) -> list[dict[str, Any]]:
        run = self.require_run(run_id)
        return self.list_run_versions(run_id, run.current_template_version_id)

    def version_number_for(
        self,
        scope_type: str,
        scope_id: str,
        version_id: str,
        current_version_id: Optional[str],
    ) -> int:
        list_fn = (
            self.list_run_versions if scope_type == "run" else self.list_workflow_versions
        )
        items = list_fn(scope_id, current_version_id)
        for item in items:
            if item["version_id"] == version_id:
                return int(item["version_number"])
        return 0

    async def branch_run_from_version(self, run_id: str, version_id: str) -> RunResult:
        """Branch from an earlier template version and start a new child run."""
        from app.services.pipeline.runner import start_run

        parent = self.require_run(run_id)
        if parent.status == "running":
            raise RunNotBranchableError("Cannot branch while run is in progress")

        root_id = resolve_root_run_id(self._repo, run_id)
        branched = self.branch_from_version(
            source_version_id=version_id,
            scope_type="run",
            scope_id=root_id,
            refine_summary="Branched from version",
        )
        payload = self.get_version_payload(branched.version_id)
        steps = planned_steps_from_json(payload.planned_steps)
        return await start_run(
            parent.upload_id,
            steps,
            parent.task_description,
            workflow_id=parent.workflow_id,
            parent_run_id=parent.run_id,
            template_id=payload.template_id,
            extraction_prompt=payload.extraction_prompt,
            current_template_version_id=branched.version_id,
            cached_documents=parent.cached_documents,
            refine_summary=branched.refine_summary,
        )

    def copy_workflow_version_to_run(
        self,
        *,
        workflow_version_id: str,
        run: RunResult,
        template_id: Optional[str],
    ) -> RunResult:
        """Seed run-scope v1 from the workflow's current template version."""
        payload = self.get_version_payload(workflow_version_id)
        steps = planned_steps_from_json(payload.planned_steps)
        return self.attach_initial_run_version(
            run,
            template_id=template_id or payload.template_id,
            planned_steps=steps,
            extraction_prompt=payload.extraction_prompt,
        )

    def build_run_version_detail(self, run_id: str, version_id: str) -> TemplateVersionDetailView:
        run = self.require_run(run_id)
        payload = self.get_version_payload(version_id)
        steps = planned_steps_from_json(payload.planned_steps)
        version_number = self.version_number_for(
            "run", run_id, version_id, run.current_template_version_id
        )
        return TemplateVersionDetailView(
            payload=payload,
            steps=steps,
            version_number=version_number,
            is_current=payload.version_id == run.current_template_version_id,
        )

    def build_workflow_version_detail(
        self,
        workflow_id: str,
        version_id: str,
        current_version_id: Optional[str],
    ) -> TemplateVersionDetailView:
        payload = self.get_version_payload(version_id)
        steps = planned_steps_from_json(payload.planned_steps)
        version_number = self.version_number_for(
            "workflow", workflow_id, version_id, current_version_id
        )
        return TemplateVersionDetailView(
            payload=payload,
            steps=steps,
            version_number=version_number,
            is_current=payload.version_id == current_version_id,
        )

    def list_run_versions(
        self, run_id: str, current_version_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        root_id = resolve_root_run_id(self._repo, run_id)
        return self._list_versions("run", root_id, current_version_id)

    def list_workflow_versions(
        self, workflow_id: str, current_version_id: Optional[str] = None
    ) -> list[dict[str, Any]]:
        return self._list_versions("workflow", workflow_id, current_version_id)

    def get_version_payload(self, version_id: str) -> UserTemplateVersionPayload:
        record = self._repo.get_template_version(version_id)
        if record is None:
            raise TemplateVersionNotFoundError(f"Version not found: {version_id}")
        raw = self._store.load_version(record.storage_key)
        return UserTemplateVersionPayload(
            version_id=record.version_id,
            scope_type=record.scope_type,
            scope_id=record.scope_id,
            template_id=record.template_id,
            extraction_prompt=str(raw.get("extraction_prompt") or ""),
            planned_steps=raw.get("planned_steps") or [],
            refine_summary=record.refine_summary,
            parent_version_id=record.parent_version_id,
            user_message=raw.get("user_message"),
            created_at=record.created_at,
        )

    def resolve_run_plan(self, run: RunResult) -> tuple[list[PlannedStep], str]:
        """Load planned steps + prompt from version or fall back to run row."""
        if run.current_template_version_id:
            payload = self.get_version_payload(run.current_template_version_id)
            steps = planned_steps_from_json(payload.planned_steps)
            prompt = payload.extraction_prompt
            return sync_prompt_to_steps(steps, prompt), prompt

        prompt = resolve_run_extraction_prompt(run.extraction_prompt, run.planned_steps)
        steps = sync_prompt_to_steps(run.planned_steps, prompt) if prompt else run.planned_steps
        return steps, prompt

    def attach_initial_run_version(
        self,
        run: RunResult,
        *,
        template_id: str,
        planned_steps: list[PlannedStep],
        extraction_prompt: str,
    ) -> RunResult:
        """Create v1 in object storage and persist run with version pointer only."""
        version = self.create_run_version(
            scope_id=run.run_id,
            template_id=template_id,
            planned_steps=planned_steps,
            extraction_prompt=extraction_prompt,
            refine_summary="Initial (from template)",
        )
        versioned = replace(run, current_template_version_id=version.version_id)
        self._repo.save_run(versioned)
        return versioned

    def hydrate_run(self, run: RunResult) -> RunResult:
        """Load planned_steps and extraction_prompt from storage when versioned."""
        if not run.current_template_version_id:
            return run
        steps, prompt = self.resolve_run_plan(run)
        return replace(run, planned_steps=steps, extraction_prompt=prompt)

    def hydrate_workflow(self, workflow: WorkflowRecord) -> WorkflowRecord:
        """Load steps and extraction_prompt from storage when versioned."""
        if not workflow.current_template_version_id:
            return workflow
        steps, prompt = self.resolve_workflow_plan(workflow)
        return replace(workflow, steps=steps, extraction_prompt=prompt)

    def delete_workflow_versions(self, workflow_id: str) -> None:
        """Remove stored payloads for all versions scoped to a workflow."""
        versions = self._repo.list_template_versions("workflow", workflow_id)
        for version in versions:
            try:
                self._store.delete_version(version.storage_key)
            except OSError:
                logger.warning(
                    "Failed to delete template version storage key=%s",
                    version.storage_key,
                    exc_info=True,
                )

    def resolve_workflow_plan(
        self, workflow: WorkflowRecord
    ) -> tuple[list[PlannedStep], str]:
        if workflow.current_template_version_id:
            payload = self.get_version_payload(workflow.current_template_version_id)
            steps = planned_steps_from_json(payload.planned_steps)
            return sync_prompt_to_steps(steps, payload.extraction_prompt), payload.extraction_prompt
        return workflow.steps, workflow.extraction_prompt or ""

    def log_refinement_event(
        self,
        *,
        template_id: str,
        scope_type: str,
        scope_id: str,
        version_id: str,
        parent_version_id: Optional[str],
        user_message: str,
        refine_summary: str,
    ) -> None:
        event = RefinementEvent(
            event_id=str(uuid.uuid4()),
            template_id=template_id,
            scope_type=scope_type,  # type: ignore[arg-type]
            scope_id=scope_id,
            version_id=version_id,
            parent_version_id=parent_version_id,
            user_message=user_message,
            refine_summary=refine_summary,
        )
        self._repo.save_refinement_event(event)

    def _create_version(
        self,
        *,
        scope_type: str,
        scope_id: str,
        template_id: str,
        planned_steps: list[PlannedStep],
        extraction_prompt: str,
        refine_summary: str,
        parent_version_id: Optional[str] = None,
        user_message: Optional[str] = None,
    ) -> UserTemplateVersionRecord:
        version_id = str(uuid.uuid4())
        existing = self._repo.list_template_versions(scope_type, scope_id)
        version_number = len(existing) + 1
        prompt = extraction_prompt.strip() or read_prompt_from_steps(planned_steps)
        steps_json = planned_steps_to_json(sync_prompt_to_steps(planned_steps, prompt))
        created_at = datetime.now(timezone.utc).isoformat()

        storage_key = self._store.build_storage_key(scope_type, scope_id, version_id)
        payload = {
            "version_id": version_id,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "template_id": template_id,
            "extraction_prompt": prompt,
            "planned_steps": steps_json,
            "refine_summary": refine_summary,
            "parent_version_id": parent_version_id,
            "user_message": user_message,
            "created_at": created_at,
        }
        self._store.save_version(storage_key, payload)

        record = UserTemplateVersionRecord(
            version_id=version_id,
            scope_type=scope_type,  # type: ignore[arg-type]
            scope_id=scope_id,
            template_id=template_id,
            storage_key=storage_key,
            version_number=version_number,
            refine_summary=refine_summary,
            parent_version_id=parent_version_id,
            created_at=created_at,
        )
        self._repo.save_template_version(record)
        return record

    def _list_versions(
        self,
        scope_type: str,
        scope_id: str,
        current_version_id: Optional[str],
    ) -> list[dict[str, Any]]:
        versions = self._repo.list_template_versions(scope_type, scope_id)
        return [
            {
                "version_id": version.version_id,
                "version_number": version.version_number,
                "refine_summary": version.refine_summary,
                "parent_version_id": version.parent_version_id,
                "is_current": version.version_id == current_version_id,
                "created_at": version.created_at,
                "template_id": version.template_id,
            }
            for version in versions
        ]
