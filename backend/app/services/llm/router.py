"""
LLM Router — picks the right LLM client based on task type.

Extraction -> OpenAI GPT-4o (json_schema mode, highest accuracy)
Plan Mode -> Groq (cheap, fast clarification)
Refiner -> Groq (complex prompt editing)
Planner -> Groq (pipeline planning)
"""

import logging
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger("llm")


class LLMTask(str, Enum):
    EXTRACTION = "extraction"
    PLAN_MODE = "plan_mode"
    REFINER = "refiner"
    PLANNER = "planner"


async def complete_json(
    system_prompt: str,
    user_prompt: str,
    *,
    task: LLMTask = LLMTask.EXTRACTION,
    model: Optional[str] = None,
    json_schema: Optional[dict[str, Any]] = None,
    return_logprobs: bool = False,
) -> Any:
    """
    Route an LLM call to the appropriate provider based on task type.

    - EXTRACTION -> OpenAI (json_schema mode for guaranteed structure)
    - PLAN_MODE, REFINER, PLANNER -> Groq (fast, cheap)
    """
    if task == LLMTask.EXTRACTION:
        from app.services.llm.openai_client import complete_json as openai_complete

        logger.info("Router: task=%s -> OpenAI", task.value)
        return await openai_complete(
            system_prompt,
            user_prompt,
            model=model,
            json_schema=json_schema,
            return_logprobs=return_logprobs,
        )

    from app.services.llm.groq_client import complete_json as groq_complete

    logger.info("Router: task=%s -> Groq", task.value)
    return await groq_complete(
        system_prompt,
        user_prompt,
        model=model,
    )
