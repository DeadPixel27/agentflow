"""Refine service — chat-driven pipeline edits and re-runs."""

from app.agents.core.context import WorkflowContext, documents_to_dicts
from app.agents.core.registry import get_handler
from app.models.domain.run import RunResult
from app.persistence.protocols import DataRepository
from app.persistence.serialization import planned_steps_from_json
from app.services.documents.upload_loader import load_upload_documents
from app.services.pipeline.extraction_prompt import sync_prompt_to_steps
from app.services.pipeline.pipeline_refiner import RefinerError
from app.services.pipeline.runner import start_run
from app.services.templates.user_template_version_service import UserTemplateVersionService

_PIPELINE_REFINER = "transform.pipeline_refiner"


class RunNotFoundError(Exception):
    """Raised when run_id does not exist."""


class RunNotRefinableError(Exception):
    """Raised when a run cannot be refined (still running, no plan, etc.)."""


class RefineService:
    def __init__(
        self,
        repo: DataRepository,
        versions: UserTemplateVersionService,
    ) -> None:
        self._repo = repo
        self._versions = versions

    async def refine_and_start(self, run_id: str, message: str) -> tuple[RunResult, str]:
        """
        Load a completed run, apply chat refinement to its pipeline, start a child run.

        Returns the new run record and a short summary of changes.
        """
        parent = self._repo.get_run(run_id)
        if parent is None:
            raise RunNotFoundError(f"Run not found: {run_id}")

        if parent.status == "running":
            raise RunNotRefinableError("Cannot refine a run that is still in progress")
        if not parent.planned_steps and not parent.current_template_version_id:
            raise RunNotRefinableError("This run has no pipeline plan to refine")

        sample_rows: list[dict] = []
        if parent.result and isinstance(parent.result.get("rows"), list):
            sample_rows = parent.result["rows"]

        planned_steps, base_prompt = self._versions.resolve_run_plan(parent)

        ctx = WorkflowContext(
            upload_id=parent.upload_id,
            task_description=message,
            data={
                "current_steps": planned_steps,
                "sample_results": sample_rows,
                "extraction_prompt": base_prompt,
            },
        )

        try:
            handler = get_handler(_PIPELINE_REFINER)
            result = await handler.execute(ctx, {})
        except ValueError as exc:
            raise RefinerError(str(exc)) from exc

        output = result.output
        new_steps = planned_steps_from_json(output.get("planned_steps"))
        summary = str(output.get("summary", "Pipeline updated.")).strip()
        new_prompt = str(output.get("extraction_prompt") or base_prompt).strip()
        new_steps = sync_prompt_to_steps(new_steps, new_prompt)

        cached_documents = parent.cached_documents
        if not cached_documents:
            documents = await load_upload_documents(parent.upload_id)
            cached_documents = documents_to_dicts(documents)

        child = await start_run(
            parent.upload_id,
            new_steps,
            parent.task_description,
            workflow_id=parent.workflow_id,
            parent_run_id=parent.run_id,
            template_id=parent.template_id,
            extraction_prompt=new_prompt,
            cached_documents=cached_documents,
            refine_summary=summary,
        )
        return child, summary
