"""
Field Extractor — uses Groq to pull structured fields from document text.

INPUT:  raw text + list of field names (+ optional instructions)
OUTPUT: dict of field → value per document
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

from app.services.llm.groq_client import complete_json
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
    parsed = await complete_json(SYSTEM_PROMPT, user_prompt)

    return _parse_llm_response(parsed, documents, fields)


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


def _build_prompt(
    documents: list[DocumentInput],
    fields: list[str],
    instructions: Optional[str],
) -> str:
    payload = {
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
                    "fields": {field: "value or null" for field in fields},
                }
            ]
        },
    }
    return json.dumps(payload, indent=2)


def _parse_llm_response(
    parsed: dict[str, Any],
    documents: list[DocumentInput],
    fields: list[str],
) -> list[ExtractedDocument]:
    raw_results = parsed.get("results", [])
    by_id = {item.get("document_id"): item for item in raw_results}

    results: list[ExtractedDocument] = []
    for doc in documents:
        item = by_id.get(doc.document_id, {})
        field_values = item.get("fields", {}) if isinstance(item, dict) else {}

        normalized = {field: field_values.get(field) for field in fields}
        results.append(
            ExtractedDocument(
                document_id=doc.document_id,
                filename=doc.filename,
                fields=normalized,
            )
        )

    return results
