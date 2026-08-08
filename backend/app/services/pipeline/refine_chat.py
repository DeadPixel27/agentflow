"""Plan Mode refinement chat — cheap clarification before expensive re-run.

Uses the fast 8b model with minimal context (field names + 2 sample rows)
to understand what the user wants. When the user confirms, returns a clear
instruction string to pass to the existing refine_and_start() method.
"""

import json
import logging
from typing import Any

from app.services.llm.groq_client import complete_json

logger = logging.getLogger("refine_chat")

_PLAN_MODEL = "llama-3.1-8b-instant"

_PLAN_SYSTEM_PROMPT = """You are a data extraction assistant in PLAN MODE. You help users clarify what they want to change in their document extraction results BEFORE running the expensive re-extraction.

You do NOT execute changes. You understand, clarify, and summarize.

CONTEXT: The user has extracted data from documents and sees results in a table. They want to fix or improve something.

YOUR JOB:
1. Understand what the user wants to change
2. If ambiguous, ask ONE specific clarifying question (not "could you elaborate?" — ask about the specific field/format/value)
3. Summarize the planned changes clearly
4. When you have enough clarity, set ready=true

RULES:
- Keep responses under 3 sentences
- Reference actual field names and sample values from the context
- Accumulate changes across multiple messages — don't reset
- When ready=true, write accumulated_instruction as a detailed, unambiguous instruction for a pipeline editor. This instruction must be self-contained — the pipeline editor will NOT see the chat history

OUTPUT FORMAT (JSON):
If still clarifying:
{"ready": false, "message": "your response", "planned_changes": ["change 1", "change 2"], "accumulated_instruction": ""}

If ready to apply:
{"ready": true, "message": "Ready to apply: [summary]. Click Apply to re-run.", "planned_changes": ["change 1"], "accumulated_instruction": "Detailed instruction for the pipeline editor: ..."}
"""


async def plan_refinement(
    message: str,
    chat_history: list[dict[str, str]],
    field_names: list[str],
    sample_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Cheap clarification turn. Uses 8b model with minimal context.

    Returns dict with: ready, message, planned_changes, accumulated_instruction
    """

    user_prompt = json.dumps(
        {
            "fields_in_results": field_names,
            "sample_values": sample_rows[:2],
            "chat_history": chat_history,
            "latest_message": message,
        },
        indent=2,
        default=str,
    )

    result = await complete_json(
        _PLAN_SYSTEM_PROMPT,
        user_prompt,
        model=_PLAN_MODEL,
    )

    return {
        "ready": bool(result.get("ready", False)),
        "message": str(
            result.get(
                "message",
                "I didn't understand that. Could you describe what field or value needs to change?",
            )
        ),
        "planned_changes": result.get("planned_changes", []),
        "accumulated_instruction": str(result.get("accumulated_instruction", "")),
    }
