"""Phase 3 — confidence scoring, validation, OCR engines, layout extraction."""

from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.extraction.confidence import compute_field_confidence
from app.services.extraction.validators import validate_extracted_fields
from app.services.documents.ocr_engines import TesseractEngine, get_ocr_engine, reset_ocr_engine
from app.services.documents.layout_extractor import extract_layout_text
from app.services.extraction.field_extractor import (
    DocumentInput,
    ExtractedDocument,
    extract_fields,
)
from app.services.llm.openai_client import LLMResult


@dataclass
class _FakeToken:
    token: str
    logprob: float


def test_compute_field_confidence_defaults_without_logprobs():
    parsed = {"results": [{"document_id": "d1", "fields": {"vendor": "Acme"}}]}
    conf = compute_field_confidence(parsed, None, ["vendor", "amount"])
    assert conf == {"vendor": 0.5, "amount": 0.5}


def test_compute_field_confidence_from_logprobs():
    # Simulate: {"vendor":"Acme"}
    tokens = [
        _FakeToken("{", -0.01),
        _FakeToken('"vendor"', -0.02),
        _FakeToken(":", -0.01),
        _FakeToken('"Acme"', -0.1),
        _FakeToken("}", -0.01),
    ]
    parsed = {
        "results": [
            {"document_id": "d1", "fields": {"vendor": "Acme"}},
        ]
    }
    conf = compute_field_confidence(parsed, tokens, ["vendor"])
    assert "vendor" in conf
    assert 0.0 <= conf["vendor"] <= 1.0
    # High probability token should score well
    assert conf["vendor"] > 0.8


def test_validate_date_format_warning():
    result = validate_extracted_fields({"invoice_date": "15/03/2024"})
    assert result.has_warnings
    assert result.warnings[0].field == "invoice_date"
    assert "YYYY-MM-DD" in result.warnings[0].message


def test_validate_amount_non_numeric():
    result = validate_extracted_fields({"total_amount": "twelve"})
    assert result.has_warnings
    assert result.warnings[0].severity == "error"
    assert "not numeric" in result.warnings[0].message


def test_validate_required_fields():
    result = validate_extracted_fields(
        {"vendor": ""},
        required_fields=["vendor"],
    )
    assert any(w.field == "vendor" and w.severity == "error" for w in result.warnings)


def test_validate_line_items_mismatch():
    result = validate_extracted_fields(
        {
            "total_amount": 100.0,
            "line_items": [
                {"amount": 40.0},
                {"amount": 40.0},
            ],
        }
    )
    assert result.has_warnings
    assert any("doesn't match" in w.message for w in result.warnings)


def test_validate_clean_invoice_no_warnings():
    result = validate_extracted_fields(
        {
            "invoice_date": "2024-03-15",
            "total_amount": 100.0,
            "line_items": [
                {"amount": 60.0},
                {"amount": 40.0},
            ],
        }
    )
    assert not result.has_warnings


def test_get_ocr_engine_falls_back_to_tesseract(monkeypatch):
    reset_ocr_engine()
    monkeypatch.setattr("app.services.documents.ocr_engines.settings.ocr_engine", "rapidocr")

    with patch(
        "app.services.documents.ocr_engines.RapidOCREngine",
        side_effect=ImportError("missing"),
    ):
        engine = get_ocr_engine()
        assert isinstance(engine, TesseractEngine)
        assert engine.name == "tesseract"
    reset_ocr_engine()


def test_get_ocr_engine_tesseract_when_configured(monkeypatch):
    reset_ocr_engine()
    monkeypatch.setattr("app.services.documents.ocr_engines.settings.ocr_engine", "tesseract")
    engine = get_ocr_engine()
    assert engine.name == "tesseract"
    reset_ocr_engine()


def test_extract_layout_text_disabled(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "app.services.documents.layout_extractor.settings.use_layout_preservation",
        False,
    )
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    assert extract_layout_text(pdf) is None


def test_extract_layout_text_skips_non_pdf(tmp_path: Path):
    img = tmp_path / "scan.png"
    img.write_bytes(b"not-a-pdf")
    assert extract_layout_text(img) is None


def test_extract_layout_text_returns_markdown(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "app.services.documents.layout_extractor.settings.use_layout_preservation",
        True,
    )
    pdf = tmp_path / "invoice.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    fake_doc = MagicMock()
    fake_doc.export_to_markdown.return_value = "# Invoice\n\n" + ("Vendor Acme Corp\n" * 10)
    fake_result = MagicMock()
    fake_result.document = fake_doc

    fake_converter_cls = MagicMock()
    fake_converter_cls.return_value.convert.return_value = fake_result

    fake_module = MagicMock()
    fake_module.DocumentConverter = fake_converter_cls

    with patch.dict(
        "sys.modules",
        {"docling": MagicMock(), "docling.document_converter": fake_module},
    ):
        text = extract_layout_text(pdf)

    assert text is not None
    assert "Invoice" in text


@pytest.mark.asyncio
async def test_extract_fields_attaches_confidence_and_validation():
    llm_payload = {
        "results": [
            {
                "document_id": "doc-1",
                "fields": {
                    "vendor": "Acme",
                    "invoice_date": "03/15/2024",
                    "total_amount": 50,
                },
            }
        ]
    }
    tokens = [
        _FakeToken("{", -0.01),
        _FakeToken('"vendor"', -0.02),
        _FakeToken(":", -0.01),
        _FakeToken('"Acme"', -0.05),
        _FakeToken(",", -0.01),
        _FakeToken('"invoice_date"', -0.02),
        _FakeToken(":", -0.01),
        _FakeToken('"03/15/2024"', -0.2),
        _FakeToken(",", -0.01),
        _FakeToken('"total_amount"', -0.02),
        _FakeToken(":", -0.01),
        _FakeToken("50", -0.05),
        _FakeToken("}", -0.01),
    ]

    with patch(
        "app.services.extraction.field_extractor.complete_json",
        return_value=LLMResult(parsed=llm_payload, logprobs=tokens),
    ):
        docs = await extract_fields(
            [DocumentInput(document_id="doc-1", text="Invoice from Acme", filename="a.pdf")],
            ["vendor", "invoice_date", "total_amount"],
        )

    assert len(docs) == 1
    assert isinstance(docs[0], ExtractedDocument)
    assert docs[0].fields["vendor"] == "Acme"
    assert "vendor" in docs[0].confidence
    assert any(w["field"] == "invoice_date" for w in docs[0].validation_warnings)


def test_text_extractor_pdf_prefers_docling(tmp_path: Path):
    from app.services.documents import text_extractor

    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    with patch(
        "app.services.documents.layout_extractor.extract_layout_text",
        return_value="# Layout markdown\n\n" + ("row\n" * 20),
    ):
        text, method = text_extractor.extract_text_from_pdf(pdf)

    assert method == "docling"
    assert "Layout markdown" in text


def test_text_extractor_image_uses_ocr_engine(tmp_path: Path):
    from PIL import Image

    from app.services.documents import text_extractor

    img_path = tmp_path / "scan.png"
    Image.new("RGB", (100, 40), color="white").save(img_path)

    fake_engine = MagicMock()
    fake_engine.name = "rapidocr"
    fake_engine.ocr_image.return_value = "Hello OCR"

    with patch(
        "app.services.documents.text_extractor.get_ocr_engine",
        return_value=fake_engine,
    ):
        text, method = text_extractor.extract_text_from_image(img_path)

    assert text == "Hello OCR"
    assert method == "rapidocr"
    fake_engine.ocr_image.assert_called_once()
