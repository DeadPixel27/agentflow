"""Tests for user template version service."""

import pytest

from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult
from app.persistence.memory_repository import MemoryRepository
from app.persistence.user_templates.local_repository import LocalUserTemplateRepository
from app.services.templates.user_template_version_service import UserTemplateVersionService


def _steps() -> list[PlannedStep]:
    return [
        PlannedStep(
            step_order=1,
            agent_type="transform.field_extractor",
            config={"fields": ["name"], "instructions": "Extract name"},
            reason="extract",
        ),
    ]


def test_create_and_list_run_versions():
    repo = MemoryRepository()
    store = LocalUserTemplateRepository()
    service = UserTemplateVersionService(repo, store)

    v1 = service.create_run_version(
        scope_id="run-1",
        template_id="resume",
        planned_steps=_steps(),
        extraction_prompt="Extract name",
        refine_summary="Initial",
    )
    v2 = service.create_run_version(
        scope_id="run-1",
        template_id="resume",
        planned_steps=_steps(),
        extraction_prompt="Extract name and email",
        refine_summary="Added email",
        parent_version_id=v1.version_id,
    )

    versions = service.list_run_versions("run-1", v2.version_id)
    assert len(versions) == 2
    assert versions[0]["version_number"] == 1
    assert versions[1]["is_current"] is True

    payload = service.get_version_payload(v2.version_id)
    assert payload.extraction_prompt == "Extract name and email"


def test_hydrate_run_loads_from_storage():
    repo = MemoryRepository()
    store = LocalUserTemplateRepository()
    service = UserTemplateVersionService(repo, store)

    run = RunResult(
        run_id="run-1",
        upload_id="upload-1",
        task_description="test",
        status="completed",
        steps=[],
        planned_steps=[],
        current_template_version_id=None,
    )
    versioned = service.attach_initial_run_version(
        run,
        template_id="resume",
        planned_steps=_steps(),
        extraction_prompt="Extract name",
    )
    stored = repo.get_run("run-1")
    assert stored is not None
    assert stored.planned_steps == []

    hydrated = service.hydrate_run(stored)
    assert len(hydrated.planned_steps) == 1
    assert hydrated.extraction_prompt == "Extract name"
    assert versioned.current_template_version_id is not None


def test_branch_from_version():
    repo = MemoryRepository()
    store = LocalUserTemplateRepository()
    service = UserTemplateVersionService(repo, store)

    v1 = service.create_run_version(
        scope_id="run-1",
        template_id="resume",
        planned_steps=_steps(),
        extraction_prompt="v1 prompt",
    )
    service.create_run_version(
        scope_id="run-1",
        template_id="resume",
        planned_steps=_steps(),
        extraction_prompt="v2 prompt",
        parent_version_id=v1.version_id,
    )
    branched = service.branch_from_version(
        source_version_id=v1.version_id,
        scope_type="run",
        scope_id="run-1",
    )
    payload = service.get_version_payload(branched.version_id)
    assert payload.extraction_prompt == "v1 prompt"
    assert branched.version_number == 3
