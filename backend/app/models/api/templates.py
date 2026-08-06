"""API models for pipeline templates."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class TemplateSummaryResponse(BaseModel):
    """List view — matches screenshot API shape."""

    template_id: str
    name: str
    description: str
    icon: str
    category: str


class TemplateResponse(TemplateSummaryResponse):
    """Full template detail."""

    task_description: str
    fields: list[str] = Field(default_factory=list)
    extraction_instructions: str = ""
    rules: list[dict[str, Any]] = Field(default_factory=list)
    output_format: str = "json"
    suggested_steps: list[str] = Field(default_factory=list)
    sort_order: int = 0
    default_task: str = ""

    @model_validator(mode="after")
    def _sync_default_task(self) -> "TemplateResponse":
        if not self.default_task:
            object.__setattr__(self, "default_task", self.task_description)
        return self

    @classmethod
    def from_domain(cls, template) -> "TemplateResponse":
        return cls(
            template_id=template.template_id,
            name=template.name,
            description=template.description,
            icon=template.icon,
            category=template.category,
            task_description=template.task_description,
            default_task=template.task_description,
            fields=list(template.fields),
            extraction_instructions=template.extraction_instructions,
            rules=list(template.rules),
            output_format=template.output_format,
            suggested_steps=list(template.suggested_steps),
            sort_order=template.sort_order,
        )


class TemplateListResponse(BaseModel):
    templates: list[TemplateSummaryResponse]
    count: int
