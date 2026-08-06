"""Seed pipeline_templates in Supabase when the table exists."""

import logging
from typing import Any, Optional

from postgrest.exceptions import APIError

from app.persistence.supabase_repository import _get_client, is_supabase_configured
from app.persistence.templates.seeds import default_templates

logger = logging.getLogger("templates")


def _api_error_code(exc: APIError) -> Optional[str]:
    if exc.args and isinstance(exc.args[0], dict):
        return exc.args[0].get("code")
    return None


def _template_rows() -> list[dict[str, Any]]:
    return [
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
        for template in default_templates()
    ]


def ensure_pipeline_templates_seeded() -> None:
    """
    Upsert code-defined templates when Supabase is configured.

    If ``pipeline_templates`` does not exist yet, logs instructions to run
    ``supabase/setup_templates.sql`` in the SQL Editor.
    """
    if not is_supabase_configured():
        return

    client = _get_client()
    try:
        client.table("pipeline_templates").select("id").limit(1).execute()
    except APIError as exc:
        if _api_error_code(exc) == "PGRST205":
            logger.warning(
                "pipeline_templates table missing. Run backend/supabase/setup_templates.sql "
                "in Supabase SQL Editor, then restart the API."
            )
            return
        raise

    rows = _template_rows()
    client.table("pipeline_templates").upsert(rows, on_conflict="id").execute()
    logger.info("Synced %d pipeline templates to Supabase", len(rows))
