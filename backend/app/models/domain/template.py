"""Pipeline template domain models."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PipelineTemplate:
    """A pre-built pipeline preset with optimized prompts and field definitions."""

    template_id: str
    name: str
    description: str
    icon: str
    category: str
    task_description: str
    fields: list[str] = field(default_factory=list)
    extraction_instructions: str = ""
    rules: list[dict[str, Any]] = field(default_factory=list)
    output_format: str = "json"
    suggested_steps: list[str] = field(default_factory=list)
    sort_order: int = 0
    is_active: bool = True

    @property
    def default_task(self) -> str:
        """Backward-compatible alias used by API and DB column ``default_task``."""
        return self.task_description

    @property
    def example_output_fields(self) -> list[str]:
        return list(self.fields)


class TemplateNotFoundError(Exception):
    """Raised when a template id does not exist or is inactive."""
