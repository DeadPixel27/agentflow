"""
Default template records — re-export from code registry.

Used to bootstrap memory storage and seed SQL. Canonical definitions live in
``app/templates/`` — keep this module in sync when adding templates.
"""

from app.models.domain.template import PipelineTemplate
from app.templates.registry import get_all_templates


def default_templates() -> list[PipelineTemplate]:
    """Canonical seed list — keep in sync with ``supabase/seed_templates.sql``."""
    return get_all_templates()
