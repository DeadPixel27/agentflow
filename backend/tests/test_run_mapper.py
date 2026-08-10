"""Tests for run API mapper enrichment."""

from app.api.mappers.run import to_run_response
from app.models.domain.pipeline import PlannedStep
from app.models.domain.run import RunResult, StepRunRecord


def _base_run(**kwargs) -> RunResult:
    defaults = dict(
        run_id="run-1",
        upload_id="upload-1",
        task_description="Extract invoices",
        status="completed",
        steps=[
            StepRunRecord(
                step_order=1,
                agent_type="transform.field_extractor",
                status="completed",
            )
        ],
        document_ids=["d1", "d2"],
        planned_steps=[
            PlannedStep(
                step_order=1,
                agent_type="transform.field_extractor",
                config={},
                reason="",
            )
        ],
        created_at="2026-08-10T04:54:00+00:00",
    )
    defaults.update(kwargs)
    return RunResult(**defaults)


def test_to_run_response_includes_created_at_and_cached_documents():
    run = _base_run(
        cached_documents=[
            {"document_id": "d1", "filename": "invoice.pdf"},
            {"document_id": "d2", "filename": "receipt.pdf"},
        ]
    )
    resp = to_run_response(run)
    assert resp.created_at == "2026-08-10T04:54:00+00:00"
    assert [(d.document_id, d.filename) for d in resp.documents] == [
        ("d1", "invoice.pdf"),
        ("d2", "receipt.pdf"),
    ]


def test_to_run_response_falls_back_to_result_rows():
    run = _base_run(
        cached_documents=None,
        result={
            "rows": [
                {"document_id": "d1", "filename": "a.pdf", "vendor": "Acme"},
                {"document_id": "d2", "filename": "b.pdf", "vendor": "Beta"},
            ]
        },
    )
    resp = to_run_response(run)
    assert [d.filename for d in resp.documents] == ["a.pdf", "b.pdf"]


def test_to_run_response_falls_back_to_document_ids():
    run = _base_run(cached_documents=None, result=None)
    resp = to_run_response(run)
    assert [(d.document_id, d.filename) for d in resp.documents] == [
        ("d1", ""),
        ("d2", ""),
    ]
