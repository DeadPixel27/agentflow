"""Template service — pipeline preset catalog and template runs."""

from typing import Optional

from app.models.domain.pipeline import PipelinePlan
from app.models.domain.template import PipelineTemplate, TemplateNotFoundError
from app.persistence.protocols import TemplateRepository
from app.services.pipeline.template_planner import create_plan_from_template


class TemplateService:
    def __init__(self, templates: TemplateRepository) -> None:
        self._templates = templates

    def list_templates(
        self,
        *,
        category: Optional[str] = None,
    ) -> list[PipelineTemplate]:
        return self._templates.list_templates(category=category, active_only=True)

    def get_template(self, template_id: str) -> PipelineTemplate:
        template = self._templates.get_template(template_id)
        if template is None or not template.is_active:
            raise TemplateNotFoundError(f"Template not found: {template_id}")
        return template

    async def build_plan(self, template_id: str, upload_id: str) -> PipelinePlan:
        template = self.get_template(template_id)
        return await create_plan_from_template(template, upload_id)
