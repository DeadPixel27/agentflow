"""Refine service — chat-driven pipeline edits and re-runs."""

import logging
import uuid
from copy import deepcopy
from dataclasses import replace
from typing import Any, Optional

from app.agents.core.context import WorkflowContext, documents_to_dicts
from app.agents.core.registry import get_handler
from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult, StepRunRecord
from app.persistence.protocols import DataRepository
from app.persistence.serialization import planned_steps_from_json
from app.services.documents.upload_loader import load_upload_documents
from app.services.pipeline.extraction_prompt import (
    effective_preview_prompt,
    sync_prompt_to_steps,
)
from app.services.pipeline.pipeline_refiner import RefinerError
from app.services.pipeline.refine_logging import log_prompt, prompt_fingerprint
from app.services.pipeline.runner import start_run
from app.services.templates.user_template_version_service import UserTemplateVersionService

_PIPELINE_REFINER = "transform.pipeline_refiner"
logger = logging.getLogger("refine_service")

_SKIP_ROW_KEYS = frozenset({"document_id", "flags", "filename"})


class RunNotFoundError(Exception):
    """Raised when run_id does not exist."""


class RunNotRefinableError(Exception):
    """Raised when a run cannot be refined (still running, no plan, etc.)."""


def _field_names_from_steps(planned_steps: list[PlannedStep]) -> list[str]:
    for step in planned_steps:
        if step.agent_type == "transform.field_extractor":
            fields = step.config.get("fields", [])
            if isinstance(fields, list):
                return [str(f) for f in fields]
    return []


def _field_names_from_result(result: Optional[dict[str, Any]]) -> list[str]:
    if not result or not isinstance(result.get("rows"), list) or not result["rows"]:
        return []
    return [
        str(key)
        for key in result["rows"][0]
        if str(key) not in _SKIP_ROW_KEYS
    ]


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
        feedback = message.strip()
        # Re-extract with the same prompt Preview used so Apply results match.
        extract_prompt = effective_preview_prompt(base_prompt, feedback)
        refiner_prompt = str(output.get("extraction_prompt") or base_prompt).strip()
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

        # Persist a reusable generalized prompt for Save Workflow.
        # Fall back to the preview merge only when the refiner returned nothing new.
        if refiner_prompt and refiner_prompt.strip() != base_prompt.strip():
            stored_prompt = refiner_prompt
        else:
            used_fallback_merge = bool(feedback)
            stored_prompt = extract_prompt if feedback else base_prompt
            if used_fallback_merge and summary == "Pipeline updated.":
                summary = "Updated extraction instructions from your feedback."
            log_prompt(
                logger,
                "apply",
                run_id=parent.run_id,
                label="fallback_merged_prompt",
                prompt=stored_prompt,
                extra={"reason": "refiner returned unchanged prompt"},
            )

        extract_fp = prompt_fingerprint(extract_prompt)
        stored_fp = prompt_fingerprint(stored_prompt)
        log_prompt(
            logger,
            "apply",
            run_id=parent.run_id,
            label="extract_prompt",
            prompt=extract_prompt,
            extra={"fp": extract_fp},
        )
        log_prompt(
            logger,
            "apply",
            run_id=parent.run_id,
            label="stored_prompt",
            prompt=stored_prompt,
            extra={
                "used_fallback_merge": used_fallback_merge,
                "fp": stored_fp,
            },
        )
        if extract_fp != stored_fp:
            logger.info(
                "[refine] extract vs generalized prompt differ parent_run_id=%s "
                "extract_fp=%s generalized_fp=%s — expected: extract matches Preview; "
                "generalized is reused by Save Workflow.",
                parent.run_id,
                extract_fp,
                stored_fp,
            )
        else:
            logger.info(
                "[refine] extract and generalized prompts match parent_run_id=%s fp=%s",
                parent.run_id,
                extract_fp,
            )

        extract_steps = sync_prompt_to_steps(new_steps, extract_prompt)

        cached_documents = parent.cached_documents
        if not cached_documents:
            documents = await load_upload_documents(parent.upload_id)
            cached_documents = documents_to_dicts(documents)

        # Targeted re-extraction: if only one field is being refined,
        # re-extract just that field (5x cheaper, same accuracy)
        from app.services.pipeline.refine_preview import _infer_target_fields

        all_fields = _field_names_from_steps(extract_steps) or _field_names_from_result(
            parent.result
        )
        target_fields = _infer_target_fields(
            message,
            [summary] if summary else [],
            list(all_fields),
        )

        if (
            len(target_fields) == 1
            and parent.result
            and isinstance(parent.result.get("rows"), list)
            and cached_documents
        ):
            child = await self._targeted_field_refine(
                parent=parent,
                extract_steps=extract_steps,
                extract_prompt=extract_prompt,
                generalized_prompt=stored_prompt,
                cached_documents=cached_documents,
                summary=summary,
                feedback=feedback,
                target_field=next(iter(target_fields)),
            )
            return child, summary

        child = await start_run(
            parent.upload_id,
            extract_steps,
            parent.task_description,
            workflow_id=parent.workflow_id,
            parent_run_id=parent.run_id,
            template_id=parent.template_id,
            extraction_prompt=extract_prompt,
            cached_documents=cached_documents,
            refine_summary=summary,
            user_id=parent.user_id,
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
                planned_steps=extract_steps,
                extraction_prompt=extract_prompt,
                generalized_prompt=stored_prompt,
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

    async def _targeted_field_refine(
        self,
        *,
        parent: RunResult,
        extract_steps: list[PlannedStep],
        extract_prompt: str,
        generalized_prompt: str,
        cached_documents: list[dict[str, Any]],
        summary: str,
        feedback: str,
        target_field: str,
    ) -> RunResult:
        """Re-extract one field across docs and save a completed child run."""
        from app.services.extraction.field_extractor import (
            DocumentInput,
            extract_single_field,
        )
        from app.services.extraction.validators import validate_extracted_fields

        logger.info(
            "[refine] targeted re-extraction for single field: %s parent_run_id=%s",
            target_field,
            parent.run_id,
        )

        updated_result = deepcopy(parent.result) or {"rows": []}
        rows = list(updated_result.get("rows") or [])
        field_confidence = dict(updated_result.get("field_confidence") or {})
        validation_warnings = dict(updated_result.get("validation_warnings") or {})

        docs_by_id = {
            str(doc.get("document_id", "")): doc
            for doc in cached_documents
            if doc.get("document_id")
        }

        for index, row in enumerate(rows):
            doc_id = str(row.get("document_id") or "")
            doc = docs_by_id.get(doc_id)
            if doc is None and len(cached_documents) == 1:
                doc = cached_documents[0]
                doc_id = str(doc.get("document_id") or doc_id)
            if doc is None:
                continue

            text = str(doc.get("text", "")).strip()
            if not text:
                continue

            new_value, confidence = await extract_single_field(
                DocumentInput(
                    document_id=doc_id or str(doc.get("document_id", "")),
                    text=text,
                    filename=str(doc.get("filename", "")),
                ),
                target_field,
                instructions=extract_prompt,
            )

            updated_row = dict(row)
            updated_row[target_field] = new_value
            if doc_id and "document_id" not in updated_row:
                updated_row["document_id"] = doc_id
            rows[index] = updated_row

            conf_key = doc_id or str(index)
            doc_conf = dict(field_confidence.get(conf_key) or {})
            doc_conf[target_field] = confidence
            field_confidence[conf_key] = doc_conf

            validation = validate_extracted_fields(
                {k: v for k, v in updated_row.items() if k not in _SKIP_ROW_KEYS}
            )
            validation_warnings[conf_key] = validation.to_dict()

        updated_result["rows"] = rows
        if field_confidence:
            updated_result["field_confidence"] = field_confidence
        if validation_warnings:
            updated_result["validation_warnings"] = validation_warnings

        child_id = str(uuid.uuid4())
        child = RunResult(
            run_id=child_id,
            upload_id=parent.upload_id,
            task_description=parent.task_description,
            status="completed",
            steps=[
                StepRunRecord(
                    step_order=step.step_order,
                    agent_type=step.agent_type,
                    status="completed",
                    output={
                        "targeted_reextraction": True,
                        "field": target_field,
                    }
                    if step.agent_type == "transform.field_extractor"
                    else {"skipped": True, "reason": "targeted_reextraction"},
                )
                for step in extract_steps
            ],
            document_ids=list(parent.document_ids),
            planned_steps=extract_steps,
            workflow_id=parent.workflow_id,
            parent_run_id=parent.run_id,
            template_id=parent.template_id,
            extraction_prompt=extract_prompt,
            cached_documents=cached_documents,
            refine_summary=summary,
            result=updated_result,
            user_id=parent.user_id,
        )

        if parent.template_id:
            version = self._versions.create_run_version(
                scope_id=child.run_id,
                template_id=parent.template_id,
                planned_steps=extract_steps,
                extraction_prompt=extract_prompt,
                generalized_prompt=generalized_prompt,
                refine_summary=summary,
                parent_version_id=parent.current_template_version_id,
                user_message=feedback or None,
            )
            child = replace(child, current_template_version_id=version.version_id)
            self._versions.log_refinement_event(
                template_id=parent.template_id,
                scope_type="run",
                scope_id=child.run_id,
                version_id=version.version_id,
                parent_version_id=parent.current_template_version_id,
                user_message=feedback,
                refine_summary=summary,
            )

        self._repo.save_run(child)
        logger.info(
            "[refine] targeted child completed parent_run_id=%s child_run_id=%s field=%s",
            parent.run_id,
            child.run_id,
            target_field,
        )
        return child
