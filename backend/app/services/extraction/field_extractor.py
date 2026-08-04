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

SYSTEM_PROMPT = """\
You are a document field extraction assistant.

Given document text and a list of field names, extract the values.
Rules:
- Return ONLY valid JSON matching the requested schema.
- Use null for fields that cannot be found in the text.
- Normalize dates to ISO format (YYYY-MM-DD) when possible.
- For amounts, return numbers without currency symbols when possible.
- Do not invent data — only extract what is present in the text.
"""


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
