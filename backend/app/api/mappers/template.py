"""Domain → API template mapping."""

from app.models.api.templates import TemplateResponse, TemplateSummaryResponse
from app.models.domain.template import PipelineTemplate


def to_template_summary(template: PipelineTemplate) -> TemplateSummaryResponse:
    return TemplateSummaryResponse(
        template_id=template.template_id,
        name=template.name,
        description=template.description,
        icon=template.icon,
        category=template.category,
    )


def to_template_response(template: PipelineTemplate) -> TemplateResponse:
    return TemplateResponse.from_domain(template)
