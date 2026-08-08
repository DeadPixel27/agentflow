"""Refine service — chat-driven pipeline edits and re-runs."""

import logging
from dataclasses import replace

from app.agents.core.context import WorkflowContext, documents_to_dicts
from app.agents.core.registry import get_handler
from app.models.domain.run import RunResult
from app.persistence.protocols import DataRepository
from app.persistence.serialization import planned_steps_from_json
from app.services.documents.upload_loader import load_upload_documents
from app.services.pipeline.extraction_prompt import merge_prompt_addition, sync_prompt_to_steps
from app.services.pipeline.pipeline_refiner import RefinerError
from app.services.pipeline.refine_logging import log_prompt, prompt_fingerprint
from app.services.pipeline.runner import start_run
from app.services.templates.user_template_version_service import UserTemplateVersionService

_PIPELINE_REFINER = "transform.pipeline_refiner"
logger = logging.getLogger("refine_service")


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

        parent = self._versions.hydrate_run(parent)

        if parent.status == "running":
            raise RunNotRefinableError("Cannot refine a run that is still in progress")
        if not parent.planned_steps and not parent.current_template_version_id:
            raise RunNotRefinableError("This run has no pipeline plan to refine")

        sample_rows: list[dict] = []
        if parent.result and isinstance(parent.result.get("rows"), list):
            sample_rows = parent.result["rows"]

        planned_steps, base_prompt = self._versions.resolve_run_plan(parent)

        logger.info(
            "[refine] apply start parent_run_id=%s template_id=%s message_len=%d",
            parent.run_id,
            parent.template_id,
            len(message),
        )
        log_prompt(
            logger,
            "apply",
            run_id=parent.run_id,
            label="base_prompt",
            prompt=base_prompt,
        )
        log_prompt(
            logger,
            "apply",
            run_id=parent.run_id,
            label="user_message_to_refiner",
            prompt=message,
        )

        refinement_history: list[str] = []
        current = parent
        seen_ids: set[str] = set()
        while current and current.parent_run_id and len(refinement_history) < 5:
            if current.run_id in seen_ids:
                break
            seen_ids.add(current.run_id)
            if current.refine_summary:
                refinement_history.append(current.refine_summary)
            prev = self._repo.get_run(current.parent_run_id)
            current = prev
        refinement_history.reverse()

        ctx = WorkflowContext(
            upload_id=parent.upload_id,
            task_description=message,
            data={
                "current_steps": planned_steps,
                "sample_results": sample_rows,
                "extraction_prompt": base_prompt,
                "previous_refinements": refinement_history,
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
        refiner_prompt = str(output.get("extraction_prompt") or base_prompt).strip()
        new_prompt = refiner_prompt
        used_fallback_merge = False

        log_prompt(
            logger,
            "apply",
            run_id=parent.run_id,
            label="refiner_output_prompt",
            prompt=refiner_prompt,
            extra={
                "refiner_changed_prompt": refiner_prompt.strip() != base_prompt.strip(),
                "refiner_summary": summary,
                "base_fp": prompt_fingerprint(base_prompt),
                "refiner_fp": prompt_fingerprint(refiner_prompt),
            },
        )

        # Only use raw feedback as fallback when the refiner returned nothing new.
        # Do NOT merge raw user text into the prompt — it contains document-specific
        # values (e.g. "should be 2.5 years") that poison extraction of other documents.
        if not new_prompt or new_prompt.strip() == base_prompt.strip():
            feedback = message.strip()
            if feedback:
                used_fallback_merge = True
                new_prompt = merge_prompt_addition(base_prompt, feedback)
                if summary == "Pipeline updated.":
                    summary = "Updated extraction instructions from your feedback."
                log_prompt(
                    logger,
                    "apply",
                    run_id=parent.run_id,
                    label="fallback_merged_prompt",
                    prompt=new_prompt,
                    extra={"reason": "refiner returned unchanged prompt"},
                )
        else:
            feedback = message.strip()

        preview_fp = prompt_fingerprint(
            merge_prompt_addition(base_prompt, message.strip())
        )
        apply_fp = prompt_fingerprint(new_prompt)
        log_prompt(
            logger,
            "apply",
            run_id=parent.run_id,
            label="final_apply_prompt",
            prompt=new_prompt,
            extra={"used_fallback_merge": used_fallback_merge},
        )
        if preview_fp != apply_fp:
            logger.warning(
                "[refine] PROMPT MISMATCH parent_run_id=%s preview_would_use_fp=%s "
                "apply_uses_fp=%s — preview merges accumulated_instruction directly; "
                "apply uses refiner output. Values may differ (e.g. years_of_experience).",
                parent.run_id,
                preview_fp,
                apply_fp,
            )
        else:
            logger.info(
                "[refine] prompt match parent_run_id=%s fp=%s",
                parent.run_id,
                apply_fp,
            )

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

        logger.info(
            "[refine] apply child started parent_run_id=%s child_run_id=%s summary=%r",
            parent.run_id,
            child.run_id,
            summary,
        )

        if parent.template_id:
            version = self._versions.create_run_version(
                scope_id=child.run_id,
                template_id=parent.template_id,
                planned_steps=new_steps,
                extraction_prompt=new_prompt,
                refine_summary=summary,
                parent_version_id=parent.current_template_version_id,
                user_message=feedback or None,
            )
            child = replace(child, current_template_version_id=version.version_id)
            self._repo.save_run(child)
            self._versions.log_refinement_event(
                template_id=parent.template_id,
                scope_type="run",
                scope_id=child.run_id,
                version_id=version.version_id,
                parent_version_id=parent.current_template_version_id,
                user_message=feedback,
                refine_summary=summary,
            )

        return child, summary
