"""Tests for owner master template apply."""

from app.persistence.templates.memory_repository import MemoryTemplateRepository
from app.persistence.user_templates.local_repository import LocalUserTemplateRepository
from app.persistence.memory_repository import MemoryRepository
from app.services.templates.template_master_refine_service import TemplateMasterRefineService


def test_apply_synthesis_updates_master_template():
    repo = MemoryRepository()
    templates = MemoryTemplateRepository()
    store = LocalUserTemplateRepository()
    service = TemplateMasterRefineService(repo, templates, store)

    synthesis = {
        "extraction_instructions": "Updated instructions from owner.",
        "fields": ["name", "email"],
        "rules": [],
    }
    updated = service.apply_synthesis("resume", synthesis)
    assert updated.extraction_instructions == "Updated instructions from owner."
    assert updated.fields == ["name", "email"]

    reloaded = templates.get_template("resume")
    assert reloaded is not None
    assert reloaded.extraction_instructions == "Updated instructions from owner."
