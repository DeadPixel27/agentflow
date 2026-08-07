"""Pipeline refiner service — LLM edits a pipeline from chat feedback."""

import json
from typing import Any

from app.agents.core.registry import get_agent_catalog
from app.config import settings
from app.models.domain.pipeline import PlannedStep
from app.services.llm.groq_client import complete_json
from app.services.pipeline.step_parse import StepParseError, parse_planned_steps
from app.validation.task_input import require_task_description

REFINE_SYSTEM_PROMPT = """\
You are a pipeline editor. Given the current pipeline definition and the user's
change request, return a MODIFIED pipeline.

Rules:
- Only change what the user asked for. Keep everything else the same.
- Return ONLY valid JSON matching the requested schema.
- Return the full pipeline (all steps), not just the changed parts.
- Use ONLY agent_type values from the available_agents catalog.
- step_order must start at 1 and increment by 1 with no gaps.
- If the user wants a new field, add it to the field_extractor step's fields list.
- If the user wants a new rule/flag, add it to the rules step's rules list.
- If the user wants a format change, update the formatter step's config.
- If the user says a field value is wrong or incorrect, update extraction_prompt with
  a clear reusable rule for future runs.
- Update field_extractor step "instructions" to match extraction_prompt.
- If a step type doesn't exist yet but is needed, add it in the correct order.
- Include a short "summary" string describing what you changed (one sentence).
- Include "extraction_prompt": the complete user-layer extraction prompt after your
  changes. This is the full prompt text, not a diff or addition.
"""


class RefinerError(Exception):
    """Raised when the pipeline refiner returns invalid output."""


async def refine_pipeline(
    current_steps: list[PlannedStep],
    sample_results: list[dict[str, Any]],
    user_message: str,
    base_prompt: str = "",
) -> tuple[list[PlannedStep], str, str]:
    """Return modified pipeline steps, summary, and full extraction_prompt."""
    message = require_task_description(user_message)
    user_prompt = _build_refine_prompt(current_steps, sample_results, message, base_prompt)

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
) -> str:
    payload = {
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
        "sample_results": sample_results[:3],
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
    return json.dumps(payload, indent=2)
