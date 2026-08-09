"""Tests for workflow deletion."""

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


def _ensure_user(repo: MemoryRepository, user_id: str = "user-1") -> None:
    repo.save_user(UserRecord(user_id=user_id, name="Test User", email="test@example.com"))


def _override(repo, versions, workflows):
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_version_service] = lambda: versions
    app.dependency_overrides[get_workflow_service] = lambda: workflows
    override_current_user()


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
    versions.attach_initial_run_version(
        run,
        template_id="resume",
        planned_steps=_steps(),
        extraction_prompt="Extract name",
    )
    return repo.get_run("run-root")


def test_delete_workflow_removes_workflow_and_versions():
    repo, versions, workflows = _setup_services()
    _ensure_user(repo)
    _seed_completed_run(repo, versions)
    workflow = workflows.create_workflow_from_run("user-1", "run-root", "My workflow")
    wf_versions = versions.list_workflow_versions(
        workflow.workflow_id, workflow.current_template_version_id
    )
    assert len(wf_versions) >= 1

    workflows.delete_workflow(workflow.workflow_id)

    assert repo.get_workflow(workflow.workflow_id) is None
    assert versions.list_workflow_versions(workflow.workflow_id, None) == []
    run = repo.get_run("run-root")
    assert run is not None
    assert run.workflow_id is None


def test_delete_workflow_api_returns_204():
    repo, versions, workflows = _setup_services()
    _ensure_user(repo)
    _seed_completed_run(repo, versions)
    workflow = workflows.create_workflow_from_run("user-1", "run-root", "My workflow")
    _override(repo, versions, workflows)

    client = TestClient(app)
    response = client.delete(f"/api/workflows/{workflow.workflow_id}")

    assert response.status_code == 204
    assert repo.get_workflow(workflow.workflow_id) is None

    app.dependency_overrides.clear()


def test_delete_workflow_api_returns_404_for_missing():
    repo, versions, workflows = _setup_services()
    _override(repo, versions, workflows)

    client = TestClient(app)
    response = client.delete("/api/workflows/missing-workflow")

    assert response.status_code == 404

    app.dependency_overrides.clear()
