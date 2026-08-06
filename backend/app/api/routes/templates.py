"""Pipeline template catalog routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.api.dependencies import TemplateServiceDep
from app.api.mappers.template import to_template_response, to_template_summary
from app.models.api.templates import TemplateListResponse, TemplateResponse, TemplateSummaryResponse
from app.models.domain.template import TemplateNotFoundError

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    templates: TemplateServiceDep,
    category: Optional[str] = Query(default=None, description="Filter by category"),
) -> TemplateListResponse:
    """List active pipeline templates (from database)."""
    items = templates.list_templates(category=category)
    responses: list[TemplateSummaryResponse] = [
        to_template_summary(item) for item in items
    ]
    return TemplateListResponse(templates=responses, count=len(responses))


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    templates: TemplateServiceDep,
) -> TemplateResponse:
    """Get one template by id."""
    try:
        return to_template_response(templates.get_template(template_id))
    except TemplateNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
