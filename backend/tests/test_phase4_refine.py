"""Phase 4 — refine preview targeting + single-field re-extraction."""

import pytest

from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult, StepRunRecord
from app.persistence.memory_repository import MemoryRepository
from app.persistence.user_templates.local_repository import LocalUserTemplateRepository
from app.services.pipeline.refine_preview import (
    _infer_target_fields,
    _values_equivalent,
    preview_refinement,
)
from app.services.pipeline.refine_service import RefineService
from app.services.templates.user_template_version_service import UserTemplateVersionService
from app.services.llm.openai_client import LLMResult


def test_infer_target_fields_underscore_and_space():
    fields = ["vendor_name", "invoice_date", "total_amount"]
    assert _infer_target_fields(
        "fix vendor name casing",
        ["Normalize vendor_name"],
        fields,
    ) == {"vendor_name"}
    assert _infer_target_fields(
        "invoice date should be YYYY-MM-DD",
        [],
        fields,
    ) == {"invoice_date"}


def test_infer_target_fields_partial_word():
    fields = ["vendor_name", "amount"]
    matched = _infer_target_fields("fix the vendor", [], fields)
    assert matched == {"vendor_name"}


def test_values_equivalent_normalization():
    assert _values_equivalent("Acme", "acme")
    assert _values_equivalent("  Foo  ", "foo")
    assert _values_equivalent(10, 10.0)
    assert _values_equivalent("10.00", 10)
    assert not _values_equivalent("Acme", "Beta")
    assert not _values_equivalent(None, "x")


@pytest.mark.asyncio
async def test_preview_skips_when_no_target_fields(monkeypatch):
    run = RunResult(
        run_id="run-1",
        upload_id="u1",
        task_description="extract",
        status="completed",
        steps=[],
        planned_steps=[
            PlannedStep(
                step_order=1,
                agent_type="transform.field_extractor",
                config={"fields": ["vendor", "amount"]},
                reason="extract",
            )
        ],
        cached_documents=[
            {
                "document_id": "doc-1",
                "filename": "a.pdf",
                "text": "Vendor Acme Amount 100",
            }
        ],
        result={"rows": [{"document_id": "doc-1", "vendor": "Acme", "amount": 100}]},
        extraction_prompt="Extract vendor and amount",
    )

    called = {"n": 0}

    async def _should_not_extract(*_args, **_kwargs):
        called["n"] += 1
        return []

    monkeypatch.setattr(
        "app.services.pipeline.refine_preview.extract_fields",
        _should_not_extract,
    )

    repo = MemoryRepository()
    versions = UserTemplateVersionService(repo, LocalUserTemplateRepository())
    preview = await preview_refinement(
        run,
        versions,
        "make the output prettier",
        ["Improve formatting"],
    )
    assert preview == []
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_preview_filters_equivalent_and_untargeted(monkeypatch):
    from app.services.extraction.field_extractor import ExtractedDocument

    run = RunResult(
        run_id="run-1",
        upload_id="u1",
        task_description="extract",
        status="completed",
        steps=[],
        planned_steps=[
            PlannedStep(
                step_order=1,
                agent_type="transform.field_extractor",
                config={"fields": ["vendor", "amount"]},
                reason="extract",
            )
        ],
        cached_documents=[
            {
                "document_id": "doc-1",
                "filename": "a.pdf",
                "text": "Vendor Acme Amount 100",
            }
        ],
        result={
            "rows": [
                {"document_id": "doc-1", "vendor": "Acme", "amount": 100},
            ]
        },
        extraction_prompt="Extract vendor and amount",
    )

    async def _fake_extract(docs, fields, instructions=None):
        return [
            ExtractedDocument(
                document_id="doc-1",
                filename="a.pdf",
                # vendor casing-only change (false diff); amount real change
                fields={"vendor": "acme", "amount": 250},
            )
        ]

    monkeypatch.setattr(
        "app.services.pipeline.refine_preview.extract_fields",
        _fake_extract,
    )

    repo = MemoryRepository()
    versions = UserTemplateVersionService(repo, LocalUserTemplateRepository())
    preview = await preview_refinement(
        run,
        versions,
        "fix amount to include tax",
        ["Update amount"],
    )
    assert len(preview) == 1
    fields = {f["field"]: f for f in preview[0]["fields"]}
    assert "amount" in fields
    assert "vendor" not in fields
    assert fields["amount"]["before"] == 100
    assert fields["amount"]["after"] == 250


@pytest.mark.asyncio
async def test_extract_single_field(monkeypatch):
    from app.services.extraction.field_extractor import DocumentInput, extract_single_field

    async def _fake_complete(*_args, **_kwargs):
        return LLMResult(
            parsed={
                "results": [
                    {
                        "document_id": "doc-1",
                        "fields": {"vendor": "Beta Corp"},
                    }
                ]
            },
            logprobs=None,
        )

    monkeypatch.setattr(
        "app.services.extraction.field_extractor.complete_json",
        _fake_complete,
    )

    value, conf = await extract_single_field(
        DocumentInput(document_id="doc-1", text="Vendor Beta Corp", filename="a.pdf"),
        "vendor",
        instructions="Prefer legal name",
    )
    assert value == "Beta Corp"
    assert conf == 0.5


@pytest.mark.asyncio
async def test_refine_and_start_targeted_single_field(monkeypatch):
    repo = MemoryRepository()
    parent = RunResult(
        run_id="run-parent",
        upload_id="upload-1",
        task_description="Extract invoice fields",
        status="completed",
        steps=[
            StepRunRecord(
                step_order=1,
                agent_type="transform.field_extractor",
                status="completed",
            ),
        ],
        document_ids=["doc-1"],
        planned_steps=[
            PlannedStep(
                step_order=1,
                agent_type="transform.field_extractor",
                config={"fields": ["vendor", "amount"]},
                reason="extract",
            ),
        ],
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
        result={
            "rows": [
                {
                    "document_id": "doc-1",
                    "filename": "inv.pdf",
                    "vendor": "Acme",
                    "amount": 1000,
                }
            ],
            "field_confidence": {"doc-1": {"vendor": 0.9, "amount": 0.8}},
        },
        template_id="invoice",
        extraction_prompt="Extract vendor and amount",
    )
    repo.save_run(parent)

    versions = UserTemplateVersionService(repo, LocalUserTemplateRepository())
    parent = versions.attach_initial_run_version(
        parent,
        template_id="invoice",
        planned_steps=parent.planned_steps,
        extraction_prompt="Extract vendor and amount",
    )
    repo.save_run(parent)

    async def _fake_execute(self, ctx, config):
        from app.agents.core.base import StepResult
        from app.persistence.serialization import planned_steps_to_json

        steps = ctx.data["current_steps"]
        return StepResult(
            output={
                "summary": "Fixed vendor casing.",
                "extraction_prompt": "Extract vendor in Title Case and amount",
                "planned_steps": planned_steps_to_json(steps),
            }
        )

    async def _fake_single(document, field, instructions=None):
        assert field == "vendor"
        return "ACME Inc", 0.95

    start_called = {"n": 0}

    async def _fake_start(*_args, **_kwargs):
        start_called["n"] += 1
        raise AssertionError("full pipeline start_run should not run for single-field refine")

    monkeypatch.setattr(
        "app.agents.handlers.transforms.pipeline_refiner.PipelineRefinerHandler.execute",
        _fake_execute,
    )
    monkeypatch.setattr(
        "app.services.extraction.field_extractor.extract_single_field",
        _fake_single,
    )
    monkeypatch.setattr(
        "app.services.pipeline.refine_service.start_run",
        _fake_start,
    )

    service = RefineService(repo, versions)
    child, summary = await service.refine_and_start(
        parent.run_id,
        "vendor should be the legal name ACME Inc",
    )

    assert start_called["n"] == 0
    assert child.status == "completed"
    assert child.parent_run_id == parent.run_id
    assert child.result["rows"][0]["vendor"] == "ACME Inc"
    assert child.result["rows"][0]["amount"] == 1000
    assert child.result["field_confidence"]["doc-1"]["vendor"] == 0.95
    assert "vendor" in summary.lower() or summary
    assert child.current_template_version_id


@pytest.mark.asyncio
async def test_refine_and_start_multi_field_uses_full_pipeline(monkeypatch):
    repo = MemoryRepository()
    parent = RunResult(
        run_id="run-parent",
        upload_id="upload-1",
        task_description="Extract invoice fields",
        status="completed",
        steps=[
            StepRunRecord(
                step_order=1,
                agent_type="transform.field_extractor",
                status="completed",
            ),
        ],
        document_ids=["doc-1"],
        planned_steps=[
            PlannedStep(
                step_order=1,
                agent_type="transform.field_extractor",
                config={"fields": ["vendor", "amount"]},
                reason="extract",
            ),
        ],
        cached_documents=[
            {
                "document_id": "doc-1",
                "filename": "inv.pdf",
                "text": "Vendor Acme Amount 1000",
            }
        ],
        result={"rows": [{"document_id": "doc-1", "vendor": "Acme", "amount": 1000}]},
        extraction_prompt="Extract vendor and amount",
    )
    repo.save_run(parent)

    versions = UserTemplateVersionService(repo, LocalUserTemplateRepository())

    async def _fake_execute(self, ctx, config):
        from app.agents.core.base import StepResult
        from app.persistence.serialization import planned_steps_to_json

        steps = ctx.data["current_steps"]
        return StepResult(
            output={
                "summary": "Updated vendor and amount rules.",
                "extraction_prompt": "Extract vendor and amount carefully",
                "planned_steps": planned_steps_to_json(steps),
            }
        )

    async def _fake_start(upload_id, steps, *args, **kwargs):
        return RunResult(
            run_id="run-child",
            upload_id=upload_id,
            task_description="Extract invoice fields",
            status="running",
            steps=[],
            planned_steps=steps,
            parent_run_id=parent.run_id,
            extraction_prompt=kwargs.get("extraction_prompt"),
            cached_documents=kwargs.get("cached_documents"),
            refine_summary=kwargs.get("refine_summary"),
        )

    monkeypatch.setattr(
        "app.agents.handlers.transforms.pipeline_refiner.PipelineRefinerHandler.execute",
        _fake_execute,
    )
    monkeypatch.setattr(
        "app.services.pipeline.refine_service.start_run",
        _fake_start,
    )

    service = RefineService(repo, versions)
    child, _summary = await service.refine_and_start(
        parent.run_id,
        "fix both vendor and amount extraction",
    )
    assert child.status == "running"
    assert child.run_id == "run-child"
