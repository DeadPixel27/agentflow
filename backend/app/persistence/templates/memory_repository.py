"""In-memory template repository — seeds match DB for local dev and tests."""

from typing import Optional

from app.models.domain.template import PipelineTemplate
from app.persistence.templates.seeds import default_templates


class MemoryTemplateRepository:
    backend_name = "memory"

    def __init__(self) -> None:
        self._templates: dict[str, PipelineTemplate] = {
            template.template_id: template for template in default_templates()
        }

    def list_templates(
        self,
        *,
        category: Optional[str] = None,
        active_only: bool = True,
    ) -> list[PipelineTemplate]:
        items = list(self._templates.values())
        if active_only:
            items = [item for item in items if item.is_active]
        if category:
            normalized = category.strip().lower()
            items = [item for item in items if item.category.lower() == normalized]
        return sorted(items, key=lambda item: (item.sort_order, item.name))

    def get_template(self, template_id: str) -> Optional[PipelineTemplate]:
        return self._templates.get(template_id)

    def save_template(self, template: PipelineTemplate) -> PipelineTemplate:
        self._templates[template.template_id] = template
        return template
