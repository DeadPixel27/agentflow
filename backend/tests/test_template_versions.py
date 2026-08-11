"""API tests for workflow template version list, preview, and revert endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_repo, get_version_service, get_workflow_service
from app.main import app
from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult, StepRunRecord
from app.models.domain.user import UserRecord
from app.persistence.memory_repository import MemoryRepository
from app.persistence.user_templates.local_repository import LocalUserTemplateRepository
from app.services.templates.user_template_version_service import UserTemplateVersionService
from app.services.users.user_service import UserService
from app.services.workflows.workflow_service import WorkflowService
from tests.auth_helpers import override_current_user

client = TestClient(app)


def _steps() -> list[PlannedStep]:
    return [
        PlannedStep(
            step_order=1,
            agent_type="transform.field_extractor",
            config={"fields": ["name"], "instructions": "Extract name"},
            reason="extract",
        ),
    ]


def _setup_services():
    repo = MemoryRepository()
    store = LocalUserTemplateRepository()
    versions = UserTemplateVersionService(repo, store)
    users = UserService(repo)
    workflows = WorkflowService(repo, users, versions)
    return repo, versions, workflows


def _seed_completed_run(repo: MemoryRepository, versions: UserTemplateVersionService) -> RunResult:
    run = RunResult(
        run_id="run-root",
        upload_id="upload-1",
        task_description="Extract fields",
        status="completed",
        steps=[
            StepRunRecord(
                step_order=1,
                agent_type="transform.field_extractor",
                status="completed",
            )
        ],
        document_ids=["doc-1"],
        planned_steps=_steps(),
        cached_documents=[
            {
                "document_id": "doc-1",
                "filename": "doc.pdf",
                "text": "Name Alice",
                "file_type": ".pdf",
                "extraction_method": "pymupdf",
                "storage_key": "k",
            }
        ],
    )
    repo.save_run(run)
    versioned = versions.attach_initial_run_version(
        run,
        template_id="resume",
        planned_steps=_steps(),
        extraction_prompt="Extract name",
    )
    v2 = versions.create_run_version(
        scope_id="run-root",
        template_id="resume",
        planned_steps=_steps(),
        extraction_prompt="Extract name and email",
        refine_summary="Added email",
        parent_version_id=versioned.current_template_version_id,
    )
    run = repo.get_run("run-root")
    assert run is not None
    from dataclasses import replace

    run = replace(run, current_template_version_id=v2.version_id)
    repo.save_run(run)
    return run


def _ensure_user(repo: MemoryRepository, user_id: str = "user-1") -> None:
    repo.save_user(UserRecord(user_id=user_id, name="Test User", email="test@example.com"))


def _override(repo, versions, workflows):
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_version_service] = lambda: versions
    app.dependency_overrides[get_workflow_service] = lambda: workflows
    override_current_user()


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_workflow_revert_updates_head():
    repo, versions, workflows = _setup_services()
    _ensure_user(repo)
    _seed_completed_run(repo, versions)
    workflow = workflows.create_workflow_from_run("user-1", "run-root", "My workflow")
    wf_versions = versions.list_workflow_versions(
        workflow.workflow_id, workflow.current_template_version_id
    )
    assert len(wf_versions) == 1
    first_version_id = wf_versions[0]["version_id"]
    first_prompt = versions.get_version_payload(first_version_id).extraction_prompt

    versions.create_workflow_version(
        scope_id=workflow.workflow_id,
        template_id="resume",
        planned_steps=_steps(),
        extraction_prompt="Updated workflow prompt",
        refine_summary="Refined workflow",
        parent_version_id=first_version_id,
    )
    workflow = repo.get_workflow(workflow.workflow_id)
    assert workflow is not None
    wf_items = versions.list_workflow_versions(workflow.workflow_id, None)
    workflow.current_template_version_id = wf_items[-1]["version_id"]
    repo.save_workflow(workflow)
    _override(repo, versions, workflows)

    response = client.post(
        f"/api/workflows/{workflow.workflow_id}/revert",
        json={"version_id": first_version_id},
    )
    assert response.status_code == 200
    updated = workflows.fetch_workflow(workflow.workflow_id)
    assert updated.current_template_version_id == response.json()["current_template_version_id"]
    assert updated.extraction_prompt == first_prompt


def test_workflow_run_seeds_run_scope_version(monkeypatch):
    from app.models.domain.upload import UploadRecord

    repo, versions, workflows = _setup_services()
    _ensure_user(repo)
    _seed_completed_run(repo, versions)
    workflow = workflows.create_workflow_from_run("user-1", "run-root", "My workflow")
    repo.save_upload(UploadRecord(upload_id="upload-1", user_id="user-1"))

    async def _fake_load(_upload_id: str):
        from app.models.domain.document import DocumentMetadata

        return [
            DocumentMetadata(
                document_id="doc-1",
                filename="doc.pdf",
                file_type=".pdf",
                storage_key="k",
            )
        ]

    async def _fake_usage(_user_id: str, _upload_id: str) -> int:
        return 1

    async def _noop_record(*_a, **_k):
        return None

    monkeypatch.setattr(
        "app.services.pipeline.runner.load_upload_documents",
        _fake_load,
    )
    monkeypatch.setattr("app.services.pipeline.runner.get_repository", lambda: repo)
    monkeypatch.setattr("app.services.pipeline.runner.save_run", repo.save_run)
    monkeypatch.setattr("app.api.usage_http.enforce_upload_usage", _fake_usage)
    monkeypatch.setattr("app.api.usage_http.charge_run_pages_or_abandon", _noop_record)
    _override(repo, versions, workflows)

    response = client.post(
        f"/api/workflows/{workflow.workflow_id}/runs",
        json={"upload_id": "upload-1"},
    )
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    run_versions = versions.list_run_versions(run_id, None)
    assert len(run_versions) == 1


def test_workflow_list_step_count_for_versioned_workflow():
    repo, versions, workflows = _setup_services()
    _ensure_user(repo)
    _seed_completed_run(repo, versions)
    workflow = workflows.create_workflow_from_run("user-1", "run-root", "My workflow")
    stored = repo.get_workflow(workflow.workflow_id)
    assert stored is not None
    stored.steps = []
    repo.save_workflow(stored)

    summaries = workflows.fetch_all_workflows()
    match = next(item for item in summaries if item.workflow_id == workflow.workflow_id)
    assert match.step_count == 1
