"""Ship-gap regression tests — metering coverage, pages, rate-limit keys, pipeline meta."""

from pathlib import Path
from unittest.mock import patch

import fitz
import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.rate_limit import _get_rate_limit_key
from app.services.analytics import events as analytics_events
from app.services.auth.jwt import create_access_token
from app.services.usage import metering
from app.services.usage.page_count import count_file_pages
from tests.auth_helpers import auth_user, override_current_user

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    metering.reset_memory_usage()
    analytics_events.reset_memory_analytics()
    monkeypatch.setattr(
        "app.persistence.supabase_repository.is_supabase_configured",
        lambda: False,
    )
    monkeypatch.setattr(settings, "free_page_limit_monthly", 50)
    monkeypatch.setattr(settings, "global_daily_page_limit", 500)
    yield
    metering.reset_memory_usage()
    analytics_events.reset_memory_analytics()
    app.dependency_overrides.clear()


def test_count_file_pages_pdf(tmp_path: Path):
    pdf = tmp_path / "multi.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.new_page()
    doc.save(pdf)
    doc.close()
    assert count_file_pages(pdf) == 3


def test_count_file_pages_image(tmp_path: Path):
    from PIL import Image

    img = tmp_path / "scan.png"
    Image.new("RGB", (10, 10), color="white").save(img)
    assert count_file_pages(img) == 1


def test_rate_limit_key_uses_jwt_user_before_deps():
    token = create_access_token("user-xyz", "x@example.com")
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
        "client": ("127.0.0.1", 123),
        "server": ("test", 80),
    }
    request = Request(scope)
    assert _get_rate_limit_key(request) == "user:user-xyz"


def test_rate_limit_key_falls_back_to_ip():
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "client": ("203.0.113.9", 123),
        "server": ("test", 80),
    }
    request = Request(scope)
    assert _get_rate_limit_key(request) == "203.0.113.9"


@pytest.mark.asyncio
async def test_get_user_id_for_run_from_memory_usage():
    await metering.record_usage("user-42", 2, run_id="run-abc")
    assert await metering.get_user_id_for_run("run-abc") == "user-42"
    assert await metering.get_user_id_for_run("missing") is None


@pytest.mark.asyncio
async def test_field_extractor_handler_stores_confidence_and_warnings():
    from app.agents.core.context import WorkflowContext
    from app.agents.handlers.transforms.field_extractor import FieldExtractorHandler
    from app.services.extraction.field_extractor import ExtractedDocument

    fake = [
        ExtractedDocument(
            document_id="d1",
            filename="a.pdf",
            fields={"vendor": "Acme", "invoice_date": "03/15/2024"},
            confidence={"vendor": 0.9, "invoice_date": 0.4},
            validation_warnings=[
                {
                    "field": "invoice_date",
                    "message": "Date not in YYYY-MM-DD format",
                    "severity": "warning",
                }
            ],
        )
    ]

    ctx = WorkflowContext(
        upload_id="u1",
        task_description="extract",
        data={
            "documents": [
                {"document_id": "d1", "filename": "a.pdf", "text": "Invoice Acme"},
            ]
        },
    )

    with patch(
        "app.agents.handlers.transforms.field_extractor.extract_fields",
        return_value=fake,
    ):
        result = await FieldExtractorHandler().execute(
            ctx,
            {"fields": ["vendor", "invoice_date"]},
        )

    assert result.output["row_count"] == 1
    assert ctx.data["rows"][0]["vendor"] == "Acme"
    assert "confidence" not in ctx.data["rows"][0]
    assert ctx.data["field_confidence"]["d1"]["vendor"] == 0.9
    assert ctx.data["validation_warnings"]["d1"][0]["field"] == "invoice_date"


@pytest.mark.asyncio
async def test_formatter_includes_confidence_in_output():
    from app.agents.core.context import WorkflowContext
    from app.agents.handlers.output.formatter import FormatterHandler

    ctx = WorkflowContext(
        upload_id="u1",
        task_description="t",
        data={
            "rows": [{"document_id": "d1", "vendor": "Acme"}],
            "field_confidence": {"d1": {"vendor": 0.95}},
            "validation_warnings": {"d1": []},
        },
    )
    await FormatterHandler().execute(ctx, {"output_format": "json"})
    output = ctx.data["output"]
    assert output["field_confidence"]["d1"]["vendor"] == 0.95
    assert "validation_warnings" in output


@pytest.mark.asyncio
async def test_extract_endpoint_enforces_usage(monkeypatch):
    monkeypatch.setattr(settings, "free_page_limit_monthly", 1)
    await metering.record_usage("user-1", 1)

    override_current_user(auth_user(user_id="user-1", email="u@example.com"))
    response = client.post(
        "/api/extract",
        json={
            "fields": ["vendor"],
            "documents": [
                {"document_id": "d1", "text": "hello", "filename": "a.pdf"}
            ],
        },
    )
    assert response.status_code == 429


def test_workflow_run_enforces_usage():
    from fastapi import HTTPException

    from app.api.dependencies import get_repo, get_workflow_service
    from app.models.domain.pipeline import PlannedStep
    from app.models.domain.user import UserRecord
    from app.models.domain.workflow import WorkflowRecord
    from app.persistence.memory_repository import MemoryRepository
    from app.services.users.user_service import UserService
    from app.services.workflows.workflow_service import WorkflowService

    repo = MemoryRepository()
    repo.save_user(UserRecord(user_id="user-1", name="A", email="u@example.com"))
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

    async def boom(*_a, **_k):
        raise HTTPException(status_code=429, detail="cap")

    override_current_user(auth_user(user_id="user-1", email="u@example.com"))
    with patch("app.api.usage_http.enforce_upload_usage", side_effect=boom):
        response = client.post(
            "/api/workflows/wf-1/runs",
            json={"upload_id": "upload-1"},
        )
    assert response.status_code == 429
    assert "cap" in response.json()["detail"]
