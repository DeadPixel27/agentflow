"""
Field Extractor — uses the LLM router to pull structured fields from document text.

INPUT:  raw text + list of field names (+ optional instructions)
OUTPUT: dict of field → value per document, plus confidence + validation warnings
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from app.services.llm.router import LLMTask, complete_json
from app.services.documents.upload_loader import load_upload_documents

logger = logging.getLogger("extract")

SYSTEM_PROMPT = """You are a precise document data extractor. Given document text and a list of fields to extract, return a JSON object with the extracted values.

CRITICAL RULES:
- Extract ONLY information explicitly present in the document. Never infer or guess.
- If a field is not clearly present, return null. It is BETTER to return null than an incorrect value.
- Search the ENTIRE document for each field — headers, footers, sidebars, tables, fine print.
- For array fields (e.g. line_items), extract ALL matching rows. Do not truncate.

NORMALIZATION RULES:
- Dates: ALWAYS return YYYY-MM-DD regardless of input format.
  Handle: DD/MM/YYYY, MM/DD/YYYY, DD.MM.YYYY, "March 15, 2024", "15th Mar '24", "15-Mar-2024".
  When ambiguous (e.g. 01/02/2024), infer from document context (country, language, other dates).
  If still ambiguous, prefer DD/MM/YYYY.
- Amounts: Return plain numbers ONLY. Strip ALL currency symbols ($, €, £, ¥, ₹),
  commas, spaces, and thousand separators.
  "$1,234.56" -> 1234.56 | "€1.234,56" -> 1234.56 | "₹1,50,000" -> 150000 | "£12,000" -> 12000
- Currency: Return ISO 4217 3-letter code. "$" -> "USD", "€" -> "EUR", "₹" -> "INR", "£" -> "GBP", "¥" -> "JPY".
  If no symbol, infer from address/locale. If unknown, return null.
- Phone numbers: Digits and + only. "+1 (555) 123-4567" -> "+15551234567"
- Names: Title Case. "JOHN DOE" -> "John Doe", "josé garcía" -> "José García".
- Tax IDs: Extract as-is (GSTIN, VAT, EIN, ABN, etc.) — do not normalize.
- Addresses: Single string with commas. Preserve structure.

RELATIVE DATES:
- The input payload includes "today". Use it for any "Present"/"Current"/"Ongoing" end date
  and for any duration or age calculation. Never guess the current date.
- Durations in years: (end - start).days / 365.25, rounded to 2 decimals.

SYNONYM AWARENESS (extract even if labeled differently):
- Invoice Number = Bill No, Reference, Factura Nr, Rechnungsnummer, Invoice #, Document Number
- Vendor/seller = Supplier, Billed From, Party Name, Company Name, From
- Buyer = Bill To, Customer, Billed To, Ship To, Purchaser
- Total Amount = Grand Total, Net Amount, Amount Due, Balance Due, Gesamtbetrag
- Tax = VAT, GST, Sales Tax, TVA, MwSt, IGST, CGST, SGST, HST
- Date = Invoice Date, Bill Date, Issue Date, Document Date, Rechnungsdatum

Return ONLY valid JSON. No markdown, no explanation, no extra text."""


@dataclass
class DocumentInput:
    document_id: str
    text: str
    filename: str = ""


@dataclass
class ExtractedDocument:
    document_id: str
    filename: str
    fields: dict[str, Any]
    confidence: dict[str, float] = field(default_factory=dict)
    validation_warnings: list[dict[str, str]] = field(default_factory=list)


async def extract_fields(
    documents: list[DocumentInput],
    fields: list[str],
    instructions: Optional[str] = None,
) -> list[ExtractedDocument]:
    """
    Extract structured fields from one or more documents in a single LLM call.
    """
    if not documents:
        return []
    if not fields:
        raise ValueError("At least one field name is required")

    user_prompt = _build_prompt(documents, fields, instructions)
    schema = _build_extraction_json_schema(fields)
    result = await complete_json(
        SYSTEM_PROMPT,
        user_prompt,
        task=LLMTask.EXTRACTION,
        json_schema=schema,
        return_logprobs=True,
    )

    from app.services.llm.openai_client import LLMResult

    if isinstance(result, LLMResult):
        parsed = result.parsed
        from app.services.extraction.confidence import compute_document_field_confidence

        confidences_by_doc = compute_document_field_confidence(
            parsed, result.logprobs, fields
        )
    else:
        parsed = result
        confidences_by_doc = {
            doc.document_id: {field_name: 0.5 for field_name in fields}
            for doc in documents
        }

    extracted_docs = _parse_llm_response(parsed, documents, fields, confidences_by_doc)

    from app.services.extraction.validators import validate_extracted_fields

    for doc_result in extracted_docs:
        validation = validate_extracted_fields(doc_result.fields)
        doc_result.validation_warnings = validation.to_dict()

    return extracted_docs


async def extract_single_field(
    document: DocumentInput,
    field: str,
    instructions: Optional[str] = None,
) -> tuple[Any, float]:
    """
    Re-extract a single field from a document.
    Returns (value, confidence) - used by targeted refinement.
    Much cheaper than full re-extraction (~5x fewer tokens).
    """
    single_prompt = _build_prompt([document], [field], instructions)
    schema = _build_extraction_json_schema([field])
    result = await complete_json(
        SYSTEM_PROMPT,
        single_prompt,
        task=LLMTask.EXTRACTION,
        json_schema=schema,
        return_logprobs=True,
    )

    from app.services.llm.openai_client import LLMResult

    if isinstance(result, LLMResult):
        parsed = result.parsed
        from app.services.extraction.confidence import compute_document_field_confidence

        conf_by_doc = compute_document_field_confidence(
            parsed, result.logprobs, [field]
        )
        conf = conf_by_doc.get(document.document_id) or next(
            iter(conf_by_doc.values()), {field: 0.5}
        )
    else:
        parsed = result
        conf = {field: 0.5}

    # Extract the value from the response
    results = parsed.get("results", [])
    if results:
        by_id = {
            item.get("document_id"): item
            for item in results
            if isinstance(item, dict)
        }
        item = by_id.get(document.document_id) or results[0]
        fields_map = item.get("fields", {}) if isinstance(item, dict) else {}
        value = fields_map.get(field)
    else:
        value = None

    return value, conf.get(field, 0.5)


async def extract_fields_from_upload(
    upload_id: str,
    fields: list[str],
    instructions: Optional[str] = None,
) -> list[ExtractedDocument]:
    """
    Load files from a prior upload batch, extract text, then run field extraction.
    """
    documents_info = await load_upload_documents(upload_id)
    if not documents_info:
        raise ValueError(f"No processable documents found for upload {upload_id}")

    documents = [
        DocumentInput(
            document_id=doc.document_id,
            filename=doc.filename,
            text=doc.text,
        )
        for doc in documents_info
        if doc.has_text
    ]

    if not documents:
        raise ValueError(f"No processable documents found for upload {upload_id}")

    return await extract_fields(documents, fields, instructions)


def _build_extraction_json_schema(fields: list[str]) -> dict[str, Any]:
    """
    OpenAI json_schema for extraction results.

    Enumerates field names so the top-level shape is constrained. Value types are
    flexible (string/number/bool/null/array/object) — strict mode is disabled in
    the client for this schema because nested free-form objects are common.
    """
    field_value = {
        "anyOf": [
            {"type": "string"},
            {"type": "number"},
            {"type": "integer"},
            {"type": "boolean"},
            {"type": "null"},
            {"type": "array"},
            {"type": "object"},
        ]
    }
    return {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string"},
                        "fields": {
                            "type": "object",
                            "properties": {
                                name: field_value for name in fields
                            },
                            "required": list(fields),
                            "additionalProperties": False,
                        },
                    },
                    "required": ["document_id", "fields"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["results"],
        "additionalProperties": False,
    }


def _build_prompt(
    documents: list[DocumentInput],
    fields: list[str],
    instructions: Optional[str],
) -> str:
    payload = {
        "today": date.today().isoformat(),
        "fields_to_extract": fields,
        "instructions": instructions or "",
        "documents": [
            {
                "document_id": doc.document_id,
                "filename": doc.filename,
                "text": doc.text,
            }
            for doc in documents
        ],
        "required_output_schema": {
            "results": [
                {
                    "document_id": "string — must match input document_id",
                    "fields": {field_name: "value or null" for field_name in fields},
                }
            ]
        },
    }
    return json.dumps(payload, indent=2)


def _parse_llm_response(
    parsed: dict[str, Any],
    documents: list[DocumentInput],
    fields: list[str],
    confidences_by_doc: dict[str, dict[str, float]] | None = None,
) -> list[ExtractedDocument]:
    raw_results = parsed.get("results", [])
    by_id = {item.get("document_id"): item for item in raw_results}

    results: list[ExtractedDocument] = []
    for doc in documents:
        item = by_id.get(doc.document_id, {})
        field_values = item.get("fields", {}) if isinstance(item, dict) else {}

        normalized = {field_name: field_values.get(field_name) for field_name in fields}
        doc_confidence = (confidences_by_doc or {}).get(doc.document_id) or {
            field_name: 0.5 for field_name in fields
        }
        results.append(
            ExtractedDocument(
                document_id=doc.document_id,
                filename=doc.filename,
                fields=normalized,
                confidence=doc_confidence,
            )
        )

    return results
