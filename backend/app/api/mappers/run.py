"""Map domain models to API responses."""

from typing import Any

from app.models.api.pipeline import PlannedStepResponse
from app.models.api.runs import RunDocumentSummary, RunResponse, StepRunResponse
from app.models.domain.run import RunResult


def _document_summaries(run: RunResult) -> list[RunDocumentSummary]:
    seen: set[str] = set()
    docs: list[RunDocumentSummary] = []

    def add(document_id: Any, filename: Any) -> None:
        if not isinstance(document_id, str) or not document_id or document_id in seen:
            return
        seen.add(document_id)
        name = filename if isinstance(filename, str) else ""
        docs.append(RunDocumentSummary(document_id=document_id, filename=name))

    for entry in run.cached_documents or []:
        if isinstance(entry, dict):
            add(entry.get("document_id"), entry.get("filename"))

    if not docs:
        rows = (run.result or {}).get("rows") if isinstance(run.result, dict) else None
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    add(row.get("document_id"), row.get("filename"))

    if not docs:
        for document_id in run.document_ids:
            add(document_id, "")

    return docs


def to_run_response(run: RunResult) -> RunResponse:
    return RunResponse(
        run_id=run.run_id,
        upload_id=run.upload_id,
        task_description=run.task_description,
        status=run.status,
        document_ids=run.document_ids,
        documents=_document_summaries(run),
        workflow_id=run.workflow_id,
        parent_run_id=run.parent_run_id,
        template_id=run.template_id,
        current_template_version_id=run.current_template_version_id,
        extraction_prompt=run.extraction_prompt,
        refine_summary=run.refine_summary,
        created_at=run.created_at,
        planned_steps=[
            PlannedStepResponse(
                step_order=step.step_order,
                agent_type=step.agent_type,
                config=step.config,
                reason=step.reason,
            )
            for step in run.planned_steps
        ],
        steps=[
            StepRunResponse(
                step_order=step.step_order,
                agent_type=step.agent_type,
                status=step.status,
                output=step.output,
                error_message=step.error_message,
            )
            for step in run.steps
        ],
        result=run.result,
        error_message=run.error_message,
    )
