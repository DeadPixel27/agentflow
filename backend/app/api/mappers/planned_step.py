"""Shared API → domain planned step mapping."""

from app.models.domain.pipeline import PlannedStep


def to_planned_steps(steps: list) -> list[PlannedStep]:
    return [
        PlannedStep(
            step_order=step.step_order,
            agent_type=step.agent_type,
            config=step.config,
            reason=step.reason,
        )
        for step in steps
    ]
