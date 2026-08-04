"""Pipeline planning domain models."""

from dataclasses import dataclass
from typing import Any


@dataclass
class PlannedStep:
    step_order: int
    agent_type: str
    config: dict[str, Any]
    reason: str


@dataclass
class PipelinePlan:
    pipeline_id: str
    upload_id: str
    task_description: str
    steps: list[PlannedStep]
    summary: str
