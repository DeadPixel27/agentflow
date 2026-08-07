"""Parse and validate planned steps from LLM JSON output."""

from typing import Any

from app.agents.core.registry import is_valid_agent_type
from app.models.domain.pipeline import PlannedStep


class StepParseError(Exception):
    """Raised when LLM returns invalid pipeline steps."""


def parse_planned_steps(parsed: dict[str, Any]) -> list[PlannedStep]:
    raw_steps = parsed.get("steps", [])
    if not raw_steps:
        raise StepParseError("Planner returned no steps")

    steps: list[PlannedStep] = []
    for item in raw_steps:
        agent_type = item.get("agent_type", "")
        if not is_valid_agent_type(agent_type):
            raise StepParseError(f"Unknown agent_type: {agent_type}")

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

    steps.sort(key=lambda step: step.step_order)
    expected_orders = list(range(1, len(steps) + 1))
    actual_orders = [step.step_order for step in steps]
    if actual_orders != expected_orders:
        raise StepParseError(
            f"Invalid step_order sequence: {actual_orders}"
        )

    return steps
