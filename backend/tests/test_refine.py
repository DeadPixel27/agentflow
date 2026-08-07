"""Tests for chat refinement pipeline editing."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_refine_service, get_repo
from app.main import app
from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult, StepRunRecord
from app.persistence.memory_repository import MemoryRepository
from app.persistence.user_templates.local_repository import LocalUserTemplateRepository
from app.services.pipeline.refine_service import RefineService
from app.services.pipeline.pipeline_refiner import RefinerError, refine_pipeline
from app.services.pipeline.step_parse import parse_planned_steps
from app.services.templates.user_template_version_service import UserTemplateVersionService

client = TestClient(app)


def _completed_run() -> RunResult:
    steps = [
        PlannedStep(
            step_order=1,
            agent_type="transform.field_extractor",
            config={"fields": ["vendor", "amount"]},
            reason="extract",
        ),
        PlannedStep(
            step_order=2,
            agent_type="output.formatter",
            config={"output_format": "csv"},
            reason="format",
        ),
    ]
    return RunResult(
        run_id="run-parent",
        upload_id="upload-1",
        task_description="Extract invoice fields",
        status="completed",
        steps=[
            StepRunRecord(step_order=1, agent_type="transform.field_extractor", status="completed"),
            StepRunRecord(step_order=2, agent_type="output.formatter", status="completed"),
        ],
        document_ids=["doc-1"],
        planned_steps=steps,
        cached_documents=[
            {
                "document_id": "doc-1",
                "filename": "inv.pdf",
                "text": "Vendor Acme Amount 1000",
                "file_type": ".pdf",
                "extraction_method": "pymupdf",
                "storage_key": "k",
            }
        ],
        result={"rows": [{"vendor": "Acme", "amount": 1000}], "format": "csv"},
    )


def test_parse_planned_steps_validates_order():
    steps = parse_planned_steps(
        {
            "steps": [
                {
                    "step_order": 1,
                    "agent_type": "output.formatter",
                    "config": {},
                    "reason": "fmt",
                }
            ]
        }
    )
    assert steps[0].agent_type == "output.formatter"


@pytest.mark.asyncio
async def test_refine_pipeline_calls_llm(monkeypatch):
    async def _fake_complete(_system: str, _user: str, **kwargs):
        return {
            "summary": "Added payment_status field.",
            "extraction_prompt": "Extract vendor and payment_status",
            "steps": [
                {
                    "step_order": 1,
                    "agent_type": "transform.field_extractor",
                    "config": {"fields": ["vendor", "amount", "payment_status"]},
                    "reason": "extract",
                },
                {
                    "step_order": 2,
                    "agent_type": "output.formatter",
                    "config": {"output_format": "csv"},
                    "reason": "format",
                },
            ],
        }

    monkeypatch.setattr(
        "app.services.pipeline.pipeline_refiner.complete_json",
        _fake_complete,
    )

    parent_steps = _completed_run().planned_steps
    new_steps, summary, prompt = await refine_pipeline(
        parent_steps,
        [{"vendor": "Acme"}],
        "also extract payment_status",
        base_prompt="Extract vendor",
    )
    assert "payment_status" in new_steps[0].config["fields"]
    assert "payment_status" in summary
    assert "payment_status" in prompt


def test_refine_run_api_starts_child_run(monkeypatch):
    repo = MemoryRepository()
    repo.save_run(_completed_run())

    async def _fake_refine(self, run_id: str, message: str):
        parent = self._repo.get_run(run_id)
        child = RunResult(
            run_id="run-child",
            upload_id=parent.upload_id,
            task_description=parent.task_description,
            status="running",
            steps=[],
            document_ids=parent.document_ids,
            planned_steps=parent.planned_steps,
            parent_run_id=parent.run_id,
            template_id="resume",
            extraction_prompt="base\n\n--- User refinement ---\nfix years",
            cached_documents=parent.cached_documents,
            refine_summary="Added payment_status.",
        )
        return child, "Added payment_status."

    monkeypatch.setattr(RefineService, "refine_and_start", _fake_refine)

    app.dependency_overrides[get_repo] = lambda: repo
    versions = UserTemplateVersionService(repo, LocalUserTemplateRepository())
    app.dependency_overrides[get_refine_service] = lambda: RefineService(repo, versions)
    try:
        response = client.post(
            "/api/runs/run-parent/refine",
            json={"message": "also extract payment_status"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["refine_summary"] == "Added payment_status."
        assert body["run"]["parent_run_id"] == "run-parent"
        assert body["run"]["status"] == "running"
    finally:
        app.dependency_overrides.clear()


def test_refine_run_rejects_running_parent():
    repo = MemoryRepository()
    run = _completed_run()
    run.status = "running"
    repo.save_run(run)

    app.dependency_overrides[get_repo] = lambda: repo
    versions = UserTemplateVersionService(repo, LocalUserTemplateRepository())
    app.dependency_overrides[get_refine_service] = lambda: RefineService(repo, versions)
    try:
        response = client.post(
            "/api/runs/run-parent/refine",
            json={"message": "add field"},
        )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()
