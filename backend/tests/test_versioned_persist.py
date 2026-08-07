"""Tests for versioned template persistence (storage pointer, no DB payload dup)."""

from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult, StepRunRecord
from app.models.domain.workflow import WorkflowRecord
from app.persistence.memory_repository import MemoryRepository
from app.persistence.versioned_persist import strip_run_for_persist, strip_workflow_for_persist


def _run_with_version() -> RunResult:
    return RunResult(
        run_id="run-1",
        upload_id="upload-1",
        task_description="test",
        status="completed",
        steps=[StepRunRecord(step_order=1, agent_type="transform.field_extractor", status="completed")],
        planned_steps=[
            PlannedStep(
                step_order=1,
                agent_type="transform.field_extractor",
                config={"fields": ["name"]},
                reason="extract",
            )
        ],
        extraction_prompt="Extract name",
        current_template_version_id="version-1",
    )


def test_strip_run_for_persist_clears_payload():
    stripped = strip_run_for_persist(_run_with_version())
    assert stripped.planned_steps == []
    assert stripped.extraction_prompt is None
    assert stripped.current_template_version_id == "version-1"


def test_strip_run_without_version_keeps_payload():
    run = _run_with_version()
    run.current_template_version_id = None
    stripped = strip_run_for_persist(run)
    assert len(stripped.planned_steps) == 1
    assert stripped.extraction_prompt == "Extract name"


def test_memory_repository_strips_versioned_run_on_save():
    repo = MemoryRepository()
    repo.save_run(_run_with_version())
    stored = repo.get_run("run-1")
    assert stored is not None
    assert stored.planned_steps == []
    assert stored.extraction_prompt is None


def test_strip_workflow_for_persist_clears_payload():
    workflow = WorkflowRecord(
        workflow_id="wf-1",
        user_id="user-1",
        name="Test",
        description="",
        source="from_run",
        task_description="",
        steps=[
            PlannedStep(
                step_order=1,
                agent_type="transform.field_extractor",
                config={},
                reason="extract",
            )
        ],
        extraction_prompt="prompt",
        current_template_version_id="version-1",
    )
    stripped = strip_workflow_for_persist(workflow)
    assert stripped.steps == []
    assert stripped.extraction_prompt is None
