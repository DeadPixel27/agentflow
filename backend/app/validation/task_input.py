"""Sanitize user-provided task text before LLM prompts."""

import re

MAX_TASK_LENGTH = 2000

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"disregard\s+(all\s+)?previous\s+instructions?",
    r"forget\s+(all\s+)?previous\s+instructions?",
    r"you\s+are\s+now\s+",
    r"new\s+instructions?:",
    r"system\s+prompt",
    r"<\s*/?\s*system\s*>",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


def sanitize_task_input(text: str) -> str:
    """Strip, truncate, and remove common prompt-injection phrases."""
    cleaned = text.strip()
    if not cleaned:
        return cleaned

    if len(cleaned) > MAX_TASK_LENGTH:
        cleaned = cleaned[:MAX_TASK_LENGTH]

    for pattern in _COMPILED:
        cleaned = pattern.sub("", cleaned)

    return cleaned.strip()


def require_task_description(text: str) -> str:
    """Sanitize task text and require non-empty content."""
    task = sanitize_task_input(text)
    if not task:
        raise ValueError("task_description is required")
    return task


def format_user_task_for_llm(text: str) -> str:
    """Wrap sanitized task text so the model treats it as untrusted user input."""
    safe = sanitize_task_input(text)
    return f"USER_TASK_START\n{safe}\nUSER_TASK_END"
