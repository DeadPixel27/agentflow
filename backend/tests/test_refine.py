"""Tests for chat refinement pipeline editing."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_refine_service, get_repo, get_version_service
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


def test_refine_plan_endpoint(monkeypatch):
    repo = MemoryRepository()
    repo.save_run(_completed_run())

    async def _fake_plan(**kwargs):
        return {
            "ready": True,
            "message": "Ready to apply: normalize dates.",
            "planned_changes": ["Normalize dates to YYYY-MM-DD"],
            "accumulated_instruction": "Normalize all dates to YYYY-MM-DD.",
        }

    async def _fake_preview(*args, **kwargs):
        return [
            {
                "document_id": "doc-1",
                "filename": "inv.pdf",
                "fields": [
                    {"field": "vendor", "before": "Acme", "after": "Acme"},
                    {"field": "amount", "before": "$1000", "after": 1000},
                ],
            }
        ]

    monkeypatch.setattr(
        "app.services.pipeline.refine_chat.plan_refinement",
        _fake_plan,
    )
    monkeypatch.setattr(
        "app.services.pipeline.refine_preview.preview_refinement",
        _fake_preview,
    )

    app.dependency_overrides[get_repo] = lambda: repo
    versions = UserTemplateVersionService(repo, LocalUserTemplateRepository())
    app.dependency_overrides[get_version_service] = lambda: versions
    try:
        response = client.post(
            "/api/runs/run-parent/refine/plan",
            json={"message": "fix the dates", "chat_history": []},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ready"] is True
        assert "dates" in body["message"].lower()
        assert body["planned_changes"] == ["Normalize dates to YYYY-MM-DD"]
        assert len(body["preview"]) == 1
        assert body["preview"][0]["fields"][1]["after"] == 1000
    finally:
        app.dependency_overrides.clear()


def test_refine_plan_not_found():
    repo = MemoryRepository()
    app.dependency_overrides[get_repo] = lambda: repo
    try:
        response = client.post(
            "/api/runs/missing/refine/plan",
            json={"message": "fix dates"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_plan_refinement_forces_ready_when_user_answers_clarification():
    from app.services.pipeline.refine_chat import _normalize_plan_result

    chat_history = [
        {"role": "user", "content": "years of experience is wrong"},
        {
            "role": "assistant",
            "content": "Can you specify the correct value for years_of_experience?",
        },
    ]
    result = _normalize_plan_result(
        {
            "ready": False,
            "message": "Can you specify the correct value for years_of_experience?",
            "planned_changes": ["change years_of_experience value"],
            "accumulated_instruction": "",
        },
        chat_history=chat_history,
        latest_message="should be 2 years, working at BNY since July 2024",
        field_names=["years_of_experience", "full_name"],
    )
    assert result["ready"] is True
    assert result["accumulated_instruction"]
    assert "years_of_experience" in result["accumulated_instruction"].lower()


@pytest.mark.asyncio
async def test_refine_and_start_merges_feedback_only_when_refiner_unchanged(monkeypatch):
    from app.services.pipeline.refine_service import RefineService

    repo = MemoryRepository()
    parent = _completed_run()
    parent.template_id = "resume"
    repo.save_run(parent)

    versions = UserTemplateVersionService(repo, LocalUserTemplateRepository())
    parent = versions.attach_initial_run_version(
        parent,
        template_id="resume",
        planned_steps=parent.planned_steps,
        extraction_prompt="Extract name",
    )
    repo.save_run(parent)

    async def _fake_execute(self, ctx, config):
        from app.agents.core.base import StepResult
        from app.persistence.serialization import planned_steps_to_json

        steps = ctx.data["current_steps"]
        return StepResult(
            output={
                "summary": "Pipeline updated.",
                "extraction_prompt": str(ctx.data.get("extraction_prompt") or ""),
                "planned_steps": planned_steps_to_json(steps),
            }
        )

    monkeypatch.setattr(
        "app.agents.handlers.transforms.pipeline_refiner.PipelineRefinerHandler.execute",
        _fake_execute,
    )
    monkeypatch.setattr("app.services.pipeline.runner.get_repository", lambda: repo)
    monkeypatch.setattr("app.services.pipeline.runner.save_run", repo.save_run)

    service = RefineService(repo, versions)
    feedback = (
        "years_of_experience should be ~2 years — calculate from BNY start date July 2024"
    )
    child, summary = await service.refine_and_start(parent.run_id, feedback)

    assert child.parent_run_id == parent.run_id
    assert child.current_template_version_id
    assert "July 2024" in (child.extraction_prompt or "")
    assert summary


@pytest.mark.asyncio
async def test_refine_and_start_does_not_poison_prompt_when_refiner_updates(monkeypatch):
    from app.services.pipeline.refine_service import RefineService

    repo = MemoryRepository()
    parent = _completed_run()
    parent.template_id = "resume"
    repo.save_run(parent)

    versions = UserTemplateVersionService(repo, LocalUserTemplateRepository())
    parent = versions.attach_initial_run_version(
        parent,
        template_id="resume",
        planned_steps=parent.planned_steps,
        extraction_prompt="Extract name",
    )
    repo.save_run(parent)

    general_rule = (
        "years_of_experience: sum durations of all work_experience entries. "
        "For each role, calculate (end_date or today) minus start_date in years."
    )

    async def _fake_execute(self, ctx, config):
        from app.agents.core.base import StepResult
        from app.persistence.serialization import planned_steps_to_json

        steps = ctx.data["current_steps"]
        return StepResult(
            output={
                "summary": "Updated years_of_experience calculation rule.",
                "extraction_prompt": f"Extract name\n\n{general_rule}",
                "planned_steps": planned_steps_to_json(steps),
            }
        )

    monkeypatch.setattr(
        "app.agents.handlers.transforms.pipeline_refiner.PipelineRefinerHandler.execute",
        _fake_execute,
    )
    monkeypatch.setattr("app.services.pipeline.runner.get_repository", lambda: repo)
    monkeypatch.setattr("app.services.pipeline.runner.save_run", repo.save_run)

    service = RefineService(repo, versions)
    feedback = (
        "years_of_experience should be ~2 years — calculate from BNY start date July 2024"
    )
    child, _summary = await service.refine_and_start(parent.run_id, feedback)

    prompt = child.extraction_prompt or ""
    assert general_rule in prompt
    assert "BNY" not in prompt
    assert "July 2024" not in prompt
    assert "2 years" not in prompt


def test_plan_refinement_forces_ready_on_repeated_assistant_message():
    from app.services.pipeline.refine_chat import _normalize_plan_result

    repeated = "You want to change years_of_experience. Can you specify the correct value?"
    chat_history = [
        {"role": "user", "content": "years of experience is wrong"},
        {"role": "assistant", "content": repeated},
        {"role": "user", "content": "2 years since July 2024 at BNY"},
        {"role": "assistant", "content": repeated},
    ]
    result = _normalize_plan_result(
        {
            "ready": False,
            "message": repeated,
            "planned_changes": ["change years_of_experience value"],
            "accumulated_instruction": "",
        },
        chat_history=chat_history,
        latest_message="yes apply that",
        field_names=["years_of_experience"],
    )
    assert result["ready"] is True
    assert "apply" in result["message"].lower()
