"""Step handler base class."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from app.agents.core.context import WorkflowContext


@dataclass
class StepResult:
    """Output from one step — stored on the step run record."""

    output: dict[str, Any]


class StepHandler(ABC):
    @abstractmethod
    async def execute(
        self,
        ctx: WorkflowContext,
        config: dict[str, Any],
    ) -> StepResult:
        pass
