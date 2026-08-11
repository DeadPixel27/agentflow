"""Admin routes — owner master template refining + OpenAI spend snapshot."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, Header, HTTPException

from app.api.dependencies import MasterRefineServiceDep
from app.config import settings
from app.services.llm.openai_cost import get_openai_spend_today

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(x_admin_key: Optional[str] = Header(default=None)) -> None:
    if not settings.admin_api_key:
        raise HTTPException(status_code=503, detail="Admin API not configured")
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin API key")


@router.get("/openai-spend")
async def openai_spend_today(
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    """In-process estimated OpenAI spend for the current UTC day."""
    return get_openai_spend_today()


templates_router = APIRouter(prefix="/templates", tags=["admin"])


@templates_router.get("/feedback")
async def list_refinement_feedback(
    master: MasterRefineServiceDep,
    template_id: Optional[str] = None,
    limit: int = 100,
    _: None = Depends(_require_admin),
) -> list[dict]:
    return master.list_feedback(template_id=template_id, limit=limit)


@templates_router.post("/{template_id}/synthesize")
async def synthesize_master_template(
    template_id: str,
    master: MasterRefineServiceDep,
    _: None = Depends(_require_admin),
) -> dict:
    try:
        return await master.synthesize(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@templates_router.post("/{template_id}/preview")
async def preview_master_template(
    template_id: str,
    synthesis: dict,
    master: MasterRefineServiceDep,
    _: None = Depends(_require_admin),
) -> dict:
    try:
        updated = master.preview_apply(template_id, synthesis)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "template_id": updated.template_id,
        "extraction_instructions": updated.extraction_instructions,
        "fields": updated.fields,
        "rules": updated.rules,
    }


@templates_router.post("/{template_id}/apply")
async def apply_master_template(
    template_id: str,
    synthesis: dict,
    master: MasterRefineServiceDep,
    _: None = Depends(_require_admin),
) -> dict:
    """Persist owner synthesis to the master template catalog."""
    try:
        updated = master.apply_synthesis(template_id, synthesis)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "template_id": updated.template_id,
        "extraction_instructions": updated.extraction_instructions,
        "fields": updated.fields,
        "rules": updated.rules,
        "message": "Master template updated.",
    }


router.include_router(templates_router)
