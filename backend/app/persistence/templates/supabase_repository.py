"""Supabase Postgres template repository."""

import logging
from typing import Optional

from postgrest.exceptions import APIError

from app.models.domain.template import PipelineTemplate
from app.persistence.supabase_repository import _get_client, is_supabase_configured
from app.persistence.templates.memory_repository import MemoryTemplateRepository

logger = logging.getLogger("db")


def _api_error_code(exc: APIError) -> Optional[str]:
    if exc.args and isinstance(exc.args[0], dict):
        return exc.args[0].get("code")
    return None


class SupabaseTemplateRepository:
    """
    Template reads use the code registry (memory fallback) as canonical source.

    Supabase ``pipeline_templates`` is kept in sync via bootstrap for admin
    visibility; code definitions in ``app/templates/`` always win at runtime.
    """

    backend_name = "supabase"

    def __init__(self) -> None:
        self._fallback = MemoryTemplateRepository()
        self._use_fallback: Optional[bool] = None

    def _probe_table(self) -> bool:
        """Return True when pipeline_templates exists and is queryable."""
        if self._use_fallback is not None:
            return not self._use_fallback
        try:
            _get_client().table("pipeline_templates").select("id").limit(1).execute()
            self._use_fallback = False
            return True
        except APIError as exc:
            code = _api_error_code(exc)
            logger.warning(
                "pipeline_templates unavailable (code=%s) — using code registry. "
                "Run backend/supabase/setup_templates.sql in Supabase SQL Editor.",
                code,
            )
            self._use_fallback = True
            return False

    def list_templates(
        self,
        *,
        category: Optional[str] = None,
        active_only: bool = True,
    ) -> list[PipelineTemplate]:
        self._probe_table()
        return self._fallback.list_templates(
            category=category,
            active_only=active_only,
        )

    def get_template(self, template_id: str) -> Optional[PipelineTemplate]:
        self._probe_table()
        return self._fallback.get_template(template_id)

    def save_template(self, template: PipelineTemplate) -> PipelineTemplate:
        self._probe_table()
        saved = self._fallback.save_template(template)
        if not self._use_fallback:
            try:
                _get_client().table("pipeline_templates").upsert(
                    {
                        "id": template.template_id,
                        "name": template.name,
                        "description": template.description,
                        "icon": template.icon,
                        "category": template.category,
                        "default_task": template.task_description,
                        "fields": template.fields,
                        "extraction_instructions": template.extraction_instructions,
                        "rules": template.rules,
                        "output_format": template.output_format,
                        "suggested_steps": template.suggested_steps,
                        "example_output_fields": template.example_output_fields,
                        "sort_order": template.sort_order,
                        "is_active": template.is_active,
                    }
                ).execute()
            except APIError as exc:
                logger.warning("Failed to persist template %s to Supabase: %s", template.template_id, exc)
        return saved


def is_template_storage_configured() -> bool:
    return is_supabase_configured()
