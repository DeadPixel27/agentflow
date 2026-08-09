"""Plan Mode refinement chat — cheap clarification before expensive re-run.

Uses the fast 8b model with minimal context (field names + 2 sample rows)
to understand what the user wants. When the user confirms, returns a clear
instruction string to pass to the existing refine_and_start() method.
"""

import json
import logging
import re
from typing import Any

from app.services.llm.router import LLMTask, complete_json

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

WHEN TO SET ready=true (do this aggressively):
- User names a field AND gives a corrected value, rule, or calculation (e.g. "should be 2 years", "use July 2024 start date")
- User answers your clarifying question with any specific detail
- User says "yes", "correct", "that's right", "apply it", "do that"
- User repeats the same correction twice — stop asking and set ready=true
- NEVER ask the same question twice. If chat_history shows you already asked, set ready=true with your best interpretation

FIELD CORRECTION EXAMPLE:
User: "years of experience is wrong, should be ~2 years"
You: {"ready": false, "message": "Got it — years_of_experience looks off. What rule should we use to calculate it?", "planned_changes": ["Fix years_of_experience calculation"], "accumulated_instruction": ""}

User: "2 years — they've worked at BNY since July 2024"
You: {"ready": true, "message": "Ready to apply: recalculate years_of_experience from employment start date (July 2024). Click Apply to re-run.", "planned_changes": ["Recalculate years_of_experience from BNY start date July 2024"], "accumulated_instruction": "Add extraction rule for years_of_experience: calculate total professional years from work_experience entries. For current role at BNY starting July 2024, count from that start date to today (~2 years). Do not use education dates. Return a numeric value."}

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

_CLARIFY_MARKERS = (
    "can you specify",
    "what should",
    "correct value",
    "which field",
    "could you clarify",
    "specify the",
    "what is the",
    "what rule",
)

_CONFIRM_MARKERS = (
    "yes",
    "yeah",
    "yep",
    "correct",
    "that's right",
    "thats right",
    "apply",
    "do it",
    "go ahead",
    "sounds good",
    "looks good",
)


def _last_assistant_message(chat_history: list[dict[str, str]]) -> str:
    for msg in reversed(chat_history):
        if msg.get("role") == "assistant":
            return str(msg.get("content", ""))
    return ""


def _user_answered_clarification(
    chat_history: list[dict[str, str]],
    latest_message: str,
) -> bool:
    last_assistant = _last_assistant_message(chat_history).lower()
    if not last_assistant:
        return False
    if not any(marker in last_assistant for marker in _CLARIFY_MARKERS) and "?" not in last_assistant:
        return False
    text = latest_message.strip()
    if len(text) < 6:
        return False
    lowered = text.lower()
    if any(marker in lowered for marker in _CONFIRM_MARKERS):
        return True
    if re.search(r"\d", text):
        return True
    if any(word in lowered for word in ("year", "month", "since", "from", "should be", "must be")):
        return True
    return len(text.split()) >= 6


def _is_repeated_assistant_response(
    chat_history: list[dict[str, str]],
    new_message: str,
) -> bool:
    last_assistant = _last_assistant_message(chat_history).strip().lower()
    if not last_assistant:
        return False
    new_normalized = new_message.strip().lower()
    if not new_normalized:
        return False
    if new_normalized == last_assistant:
        return True
    # Same question rephrased — high overlap
    last_words = set(last_assistant.split())
    new_words = set(new_normalized.split())
    if len(last_words) < 4:
        return False
    overlap = len(last_words & new_words) / max(len(last_words), 1)
    return overlap >= 0.75


def _collect_user_context(
    chat_history: list[dict[str, str]],
    latest_message: str,
) -> str:
    parts = [
        str(msg.get("content", "")).strip()
        for msg in chat_history
        if msg.get("role") == "user" and str(msg.get("content", "")).strip()
    ]
    if latest_message.strip():
        parts.append(latest_message.strip())
    return " ".join(parts)


def _build_accumulated_instruction(
    chat_history: list[dict[str, str]],
    latest_message: str,
    planned_changes: list[str],
    field_names: list[str],
) -> str:
    user_context = _collect_user_context(chat_history, latest_message)
    changes = "; ".join(planned_changes) if planned_changes else user_context
    fields_hint = ", ".join(field_names[:12]) if field_names else "relevant fields"
    return (
        "Update the extraction pipeline based on this user feedback. "
        f"User said: {user_context}. "
        f"Planned changes: {changes}. "
        f"Fields in results: {fields_hint}. "
        "Add reusable extraction_prompt rules (general, not document-specific) "
        "so future runs extract correctly. Do not hardcode one document's values."
    )


def _normalize_plan_result(
    result: dict[str, Any],
    *,
    chat_history: list[dict[str, str]],
    latest_message: str,
    field_names: list[str],
) -> dict[str, Any]:
    message = str(
        result.get(
            "message",
            "I didn't understand that. Could you describe what field or value needs to change?",
        )
    )
    planned_changes = list(result.get("planned_changes") or [])
    ready = bool(result.get("ready", False))
    accumulated = str(result.get("accumulated_instruction") or "").strip()

    user_answered = _user_answered_clarification(chat_history, latest_message)
    repeated = _is_repeated_assistant_response(chat_history, message)

    if not ready and (user_answered or repeated):
        ready = True
        if not accumulated:
            accumulated = _build_accumulated_instruction(
                chat_history,
                latest_message,
                planned_changes,
                field_names,
            )
        if repeated:
            message = (
                "Ready to apply your corrections. Click Apply to re-run extraction "
                "with the updated rules."
            )
        elif not message.lower().startswith("ready to apply"):
            summary = ", ".join(planned_changes) if planned_changes else "your corrections"
            message = f"Ready to apply: {summary}. Click Apply to re-run."

    return {
        "ready": ready,
        "message": message,
        "planned_changes": planned_changes,
        "accumulated_instruction": accumulated,
    }


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
        task=LLMTask.PLAN_MODE,
        model=_PLAN_MODEL,
    )

    return _normalize_plan_result(
        result,
        chat_history=chat_history,
        latest_message=message,
        field_names=field_names,
    )
