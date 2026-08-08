"""Pipeline refiner service — LLM edits a pipeline from chat feedback."""

import json
from typing import Any, Optional

from app.agents.core.registry import get_agent_catalog
from app.config import settings
from app.models.domain.pipeline import PlannedStep
from app.services.llm.groq_client import complete_json
from app.services.pipeline.step_parse import StepParseError, parse_planned_steps
from app.validation.task_input import require_task_description

REFINE_SYSTEM_PROMPT = """You are a pipeline editor. Given the current pipeline definition, sample extraction results, and the user's change request, return a MODIFIED pipeline.

REFINEMENT TYPES - identify which type the user is requesting:

1. FIELD CORRECTION - user says a value is wrong or formatted incorrectly
   -> Add a reusable rule to extraction_prompt, NOT a one-time fix
   -> Make rules GENERAL (e.g. "Dates in DD/MM format -> YYYY-MM-DD") not document-specific
   -> NEVER hardcode a specific correct value into extraction_prompt

2. ADD FIELD - user wants additional data extracted
   -> Add the field to the field_extractor step's config.fields list
   -> Add guidance to extraction_prompt explaining where to find the new field

3. REMOVE FIELD - user doesn't need a field
   -> Remove from config.fields
   -> Clean up any related extraction_prompt instructions

4. ADD RULE - user wants flagging/filtering
   -> Add to rules step config.rules (create a rules step if one doesn't exist)
   -> Available operators: gt, lt, eq, neq, contains

5. FORMAT CHANGE - user wants different output format
   -> Update formatter step config

CRITICAL RULES:
- Only change what the user asked for. Keep everything else EXACTLY the same.
- Do NOT modify fields that the user didn't mention.
- Do NOT remove fields unless explicitly asked.
- Return the FULL pipeline (all steps), not just the changed parts.
- Use ONLY agent_type values from the available_agents catalog.
- extraction_prompt must be the COMPLETE updated prompt (not just additions).
- When writing extraction_prompt rules, make them GENERAL and REUSABLE:
  BAD:  "The date in document abc-123 should be 2024-03-15"
  GOOD: "Dates in this vendor's invoices use DD/MM/YYYY format. Normalize to YYYY-MM-DD."
- Verify your output has all original fields plus additions minus explicit removals.

EXAMPLE:
User: "the amounts still have dollar signs, and also extract payment_status"
Current fields: ["vendor_name", "invoice_number", "total_amount", "invoice_date"]
Sample results: [{"vendor_name": "Acme", "total_amount": "$1,234", "invoice_date": "2024-03-15"}]

Expected changes:
1. Add amount normalization rule to extraction_prompt
2. Add "payment_status" to config.fields
3. Add guidance for payment_status to extraction_prompt
4. Keep all other fields and steps unchanged

Expected extraction_prompt update:
"...existing instructions..."
Amounts: Return plain numbers only. Strip all currency symbols ($, €, ₹, £). No commas. $1,234 -> 1234.
payment_status: Look for 'Paid', 'Unpaid', 'Pending', 'Overdue', 'Due'. Return one of: paid, unpaid, pending, overdue. Null if not stated."

PREVIOUS REFINEMENTS (if provided):
If previous_refinements is present, these are summaries of what was already tried.
Do NOT undo previous fixes unless the user explicitly asks.
Build on previous refinements, don't reset them."""


class RefinerError(Exception):
    """Raised when the pipeline refiner returns invalid output."""


async def refine_pipeline(
    current_steps: list[PlannedStep],
    sample_results: list[dict[str, Any]],
    user_message: str,
    base_prompt: str = "",
    previous_refinements: Optional[list[str]] = None,
) -> tuple[list[PlannedStep], str, str]:
    """Return modified pipeline steps, summary, and full extraction_prompt."""
    message = require_task_description(user_message)
    user_prompt = _build_refine_prompt(
        current_steps,
        sample_results,
        message,
        base_prompt,
        previous_refinements or [],
    )

    try:
        parsed = await complete_json(
            REFINE_SYSTEM_PROMPT,
            user_prompt,
            model=settings.groq_refiner_model,
        )
        steps = parse_planned_steps(parsed)
    except StepParseError as exc:
        raise RefinerError(str(exc)) from exc

    summary = str(parsed.get("summary", "Pipeline updated.")).strip()
    extraction_prompt = str(parsed.get("extraction_prompt") or "").strip()
    if not extraction_prompt:
        extraction_prompt = base_prompt.strip() or read_prompt_from_steps(steps)
    return steps, summary or "Pipeline updated.", extraction_prompt


def read_prompt_from_steps(steps: list[PlannedStep]) -> str:
    for step in steps:
        if step.agent_type == "transform.field_extractor":
            return str(step.config.get("instructions") or "").strip()
    return ""


def _build_refine_prompt(
    current_steps: list[PlannedStep],
    sample_results: list[dict[str, Any]],
    user_message: str,
    base_prompt: str,
    previous_refinements: list[str],
) -> str:
    payload: dict[str, Any] = {
        "current_extraction_prompt": base_prompt,
        "current_pipeline": [
            {
                "step_order": step.step_order,
                "agent_type": step.agent_type,
                "config": step.config,
                "reason": step.reason,
            }
            for step in current_steps
        ],
        "sample_results": sample_results[:10],
        "user_change_request": user_message,
        "available_agents": get_agent_catalog(),
        "required_output_schema": {
            "summary": "One sentence describing what changed",
            "extraction_prompt": "Complete user-layer extraction prompt after changes",
            "steps": [
                {
                    "step_order": 1,
                    "agent_type": "must be valid agent_type",
                    "config": {},
                    "reason": "why this step exists",
                }
            ],
        },
    }
    if previous_refinements:
        payload["previous_refinements"] = previous_refinements
    return json.dumps(payload, indent=2)
