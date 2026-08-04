"""Helpers for serializing pipeline steps to/from JSON."""

from typing import Any, List, Optional

from app.models.domain.pipeline import PlannedStep


def planned_steps_to_json(steps: list[PlannedStep]) -> list[dict[str, Any]]:
    return [
        {
            "step_order": step.step_order,
            "agent_type": step.agent_type,
            "config": step.config,
            "reason": step.reason,
        }
        for step in steps
    ]


def planned_steps_from_json(data: Optional[List[dict[str, Any]]]) -> list[PlannedStep]:
    if not data:
        return []
    return [
        PlannedStep(
            step_order=int(item["step_order"]),
            agent_type=item["agent_type"],
            config=item.get("config") or {},
            reason=item.get("reason") or "",
        )
        for item in data
    ]
