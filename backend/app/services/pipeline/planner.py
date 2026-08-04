"""
Planner — turns a task description + document context into a step pipeline.
"""

import json
import logging
import uuid
from typing import Any

from app.agents.core.registry import get_agent_catalog, is_valid_agent_type
from app.models.domain.pipeline import PipelinePlan, PlannedStep
from app.services.llm.groq_client import complete_json
from app.services.documents.upload_loader import UploadDocumentInfo, load_upload_documents

logger = logging.getLogger("planner")

SYSTEM_PROMPT = """\
You are a document processing pipeline planner.

Given a user's task and document metadata, produce an ordered list of processing steps.
Each step uses one agent_type from the available catalog.

Rules:
- Return ONLY valid JSON matching the requested schema.
- Use ONLY agent_type values from the catalog.
- step_order must start at 1 and increment by 1 with no gaps.
- Always end with output.formatter when the user wants CSV, JSON, Excel, or a table.
- Use transform.field_extractor when the user wants specific data fields extracted.
- Use transform.rules when the user wants flags, filters, or conditions (e.g. "over 50K").
- processor.ocr: use for images (.png, .jpg) or when extraction_method is "tesseract".
- processor.text_extract: use for digital PDFs when extraction_method is "pymupdf".
- If documents_already_have_text is true, SKIP processor.ocr and processor.text_extract
  because text was already extracted at upload time.
- Put all step-specific settings in config (field names, thresholds, output format, etc.).
- config must be an object (use {} when there are no settings).
"""


async def create_plan(
    upload_id: str,
    task_description: str,
) -> PipelinePlan:
    """Build a pipeline plan from an upload batch and task description."""
    task = task_description.strip()
    if not task:
        raise ValueError("task_description is required")

    documents = await load_upload_documents(upload_id)
    if not documents:
        raise ValueError(f"No documents found for upload {upload_id}")

    user_prompt = _build_prompt(task, documents)
    parsed = await complete_json(SYSTEM_PROMPT, user_prompt)
    steps = _parse_and_validate_steps(parsed)

    return PipelinePlan(
        pipeline_id=str(uuid.uuid4()),
        upload_id=upload_id,
        task_description=task,
        steps=steps,
        summary=parsed.get("summary", ""),
    )


def _build_prompt(
    task_description: str,
    documents: list[UploadDocumentInfo],
) -> str:
    all_have_text = all(doc.has_text for doc in documents)

    payload = {
        "task_description": task_description,
        "documents_already_have_text": all_have_text,
        "document_count": len(documents),
        "documents": [
            {
                "document_id": doc.document_id,
                "filename": doc.filename,
                "file_type": doc.file_type,
                "extraction_method": doc.extraction_method,
                "char_count": len(doc.text),
                "text_preview": doc.text_preview,
            }
            for doc in documents
        ],
        "available_agents": get_agent_catalog(),
        "required_output_schema": {
            "summary": "One sentence describing the planned pipeline",
            "steps": [
                {
                    "step_order": 1,
                    "agent_type": "must be a key from available_agents",
                    "config": {"example": "step-specific settings"},
                    "reason": "Why this step is needed",
                }
            ],
        },
    }
    return json.dumps(payload, indent=2)


def _parse_and_validate_steps(parsed: dict[str, Any]) -> list[PlannedStep]:
    raw_steps = parsed.get("steps", [])
    if not raw_steps:
        raise RuntimeError("Planner returned no steps")

    steps: list[PlannedStep] = []
    for item in raw_steps:
        agent_type = item.get("agent_type", "")
        if not is_valid_agent_type(agent_type):
            raise RuntimeError(f"Planner returned unknown agent_type: {agent_type}")

        config = item.get("config", {})
        if not isinstance(config, dict):
            config = {}

        steps.append(
            PlannedStep(
                step_order=int(item.get("step_order", len(steps) + 1)),
                agent_type=agent_type,
                config=config,
                reason=str(item.get("reason", "")),
            )
        )

    steps.sort(key=lambda s: s.step_order)
    expected_orders = list(range(1, len(steps) + 1))
    actual_orders = [s.step_order for s in steps]
    if actual_orders != expected_orders:
        raise RuntimeError(
            f"Planner returned invalid step_order sequence: {actual_orders}"
        )

    return steps
