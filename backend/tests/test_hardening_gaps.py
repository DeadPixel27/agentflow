"""Hardening gap tests — ownership, inbound metering, refunds, json_schema."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_repo, get_workflow_service
from app.main import app
from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult, StepRunRecord
from app.models.domain.user import UserRecord
from app.models.domain.workflow import WorkflowRecord
from app.persistence.memory_repository import MemoryRepository
from app.services.extraction.confidence import compute_document_field_confidence
from app.services.extraction.field_extractor import _build_extraction_json_schema
from app.services.usage import metering
from app.services.users.user_service import UserService
from app.services.workflows.workflow_service import WorkflowService
from tests.auth_helpers import auth_user, override_current_user

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    metering.reset_memory_usage()
    yield
    metering.reset_memory_usage()
    app.dependency_overrides.clear()


def test_build_extraction_json_schema_enumerates_fields():
    schema = _build_extraction_json_schema(["vendor", "amount"])
    props = schema["properties"]["results"]["items"]["properties"]["fields"]["properties"]
    assert set(props) == {"vendor", "amount"}
    assert schema["required"] == ["results"]


def test_compute_document_field_confidence_is_per_doc():
    parsed = {
        "results": [
            {"document_id": "d1", "fields": {"vendor": "Acme"}},
            {"document_id": "d2", "fields": {"vendor": "Beta"}},
        ]
    }
    by_doc = compute_document_field_confidence(parsed, None, ["vendor"])
    assert by_doc["d1"]["vendor"] == 0.5
    assert by_doc["d2"]["vendor"] == 0.5


@pytest.mark.asyncio
async def test_refund_usage_for_failed_run(monkeypatch):
    monkeypatch.setattr(
        "app.services.usage.metering._supabase_client",
        lambda: None,
    )
    await metering.record_usage("user-1", 3, run_id="run-x", event_type="extraction")
    assert await metering.get_user_usage_this_month("user-1") == 3

    await metering.refund_usage_for_run("run-x", reason="run_failed")
    assert await metering.get_user_usage_this_month("user-1") == 0


def test_get_run_forbids_other_user():
    repo = MemoryRepository()
    repo.save_user(UserRecord(user_id="user-1", name="A", email="a@example.com"))
    repo.save_user(UserRecord(user_id="user-2", name="B", email="b@example.com"))
    repo.save_run(
        RunResult(
            run_id="run-owned",
            upload_id="u1",
            task_description="t",
            status="completed",
            steps=[],
            user_id="user-1",
        )
    )
    app.dependency_overrides[get_repo] = lambda: repo
    override_current_user(auth_user(user_id="user-2"))

    response = client.get("/api/runs/run-owned")
    assert response.status_code == 403


def test_get_run_allows_owner():
    repo = MemoryRepository()
    repo.save_user(UserRecord(user_id="user-1", name="A", email="a@example.com"))
    repo.save_run(
        RunResult(
            run_id="run-owned",
            upload_id="u1",
            task_description="t",
            status="completed",
            steps=[
                StepRunRecord(
                    step_order=1,
                    agent_type="transform.field_extractor",
                    status="completed",
                )
            ],
            user_id="user-1",
            planned_steps=[
                PlannedStep(
                    step_order=1,
                    agent_type="transform.field_extractor",
                    config={"fields": ["vendor"]},
                    reason="x",
                )
            ],
        )
    )
    app.dependency_overrides[get_repo] = lambda: repo
    override_current_user(auth_user(user_id="user-1"))

    response = client.get("/api/runs/run-owned")
    assert response.status_code == 200


def test_list_workflows_scoped_to_current_user():
    repo = MemoryRepository()
    repo.save_user(UserRecord(user_id="user-1", name="A", email="a@example.com"))
    repo.save_user(UserRecord(user_id="user-2", name="B", email="b@example.com"))
    repo.save_workflow(
        WorkflowRecord(
            workflow_id="wf-1",
            user_id="user-1",
            name="Mine",
            description="",
            source="adhoc",
            task_description="",
            steps=[],
        )
    )
    repo.save_workflow(
        WorkflowRecord(
            workflow_id="wf-2",
            user_id="user-2",
            name="Theirs",
            description="",
            source="adhoc",
            task_description="",
            steps=[],
        )
    )
    users = UserService(repo)
    workflows = WorkflowService(repo, users, None)
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_workflow_service] = lambda: workflows
    override_current_user(auth_user(user_id="user-1"))

    response = client.get("/api/workflows")
    assert response.status_code == 200
    ids = {row["workflow_id"] for row in response.json()}
    assert ids == {"wf-1"}


def test_users_list_all_removed():
    override_current_user()
    response = client.get("/api/users")
    # /api/users no longer lists everyone — either 404/405 or hits /{user_id}
    assert response.status_code in (404, 405, 422)


def test_inbound_rejects_when_secret_missing(monkeypatch):
    monkeypatch.setattr("app.api.routes.inbound.settings.inbound_webhook_secret", "")
    response = client.post("/api/inbound/email", data={"recipient": "x@y.com"})
    assert response.status_code == 403


def test_workflow_run_enforces_usage_after_ownership():
    repo = MemoryRepository()
    repo.save_user(UserRecord(user_id="user-1", name="A", email="a@example.com"))
    repo.save_workflow(
        WorkflowRecord(
            workflow_id="wf-1",
            user_id="user-1",
            name="Mine",
            description="",
            source="adhoc",
            task_description="",
            steps=[
                PlannedStep(
                    step_order=1,
                    agent_type="transform.field_extractor",
                    config={"fields": ["vendor"]},
                    reason="x",
                )
            ],
        )
    )
    users = UserService(repo)
    workflows = WorkflowService(repo, users, None)
    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_workflow_service] = lambda: workflows
    override_current_user(auth_user(user_id="user-1"))

    from fastapi import HTTPException

    async def boom(*_a, **_k):
        raise HTTPException(status_code=429, detail="cap")

    with patch("app.api.usage_http.enforce_upload_usage", side_effect=boom):
        response = client.post(
            "/api/workflows/wf-1/runs",
            json={"upload_id": "upload-1"},
        )
    assert response.status_code == 429
