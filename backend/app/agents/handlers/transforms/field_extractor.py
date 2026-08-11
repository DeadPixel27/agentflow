"""LLM field extraction from document text."""

from typing import Any

from app.agents.core.base import StepHandler, StepResult
from app.agents.core.context import WorkflowContext
from app.agents.core.registry import register_agent
from app.services.extraction.field_extractor import DocumentInput, extract_fields


class FieldExtractorHandler(StepHandler):
    async def execute(
        self,
        ctx: WorkflowContext,
        config: dict[str, Any],
    ) -> StepResult:
        fields = config.get("fields", [])
        if not fields:
            raise ValueError("field_extractor config requires 'fields'")

        documents = ctx.data.get("documents", [])
        doc_inputs = [
            DocumentInput(
                document_id=doc["document_id"],
                filename=doc.get("filename", ""),
                text=doc.get("text", ""),
            )
            for doc in documents
            if doc.get("text", "").strip()
        ]

        if not doc_inputs:
            raise ValueError("No document text available for field extraction")

        extracted = await extract_fields(
            doc_inputs,
            fields,
            str(config.get("instructions") or "").strip(),
        )

        # Flat rows for CSV / rules agents (field values only)
        rows = [
            {
                "document_id": item.document_id,
                "filename": item.filename,
                **item.fields,
            }
            for item in extracted
        ]
        ctx.data["rows"] = rows

        # Confidence + validation kept separate so CSV stays clean
        ctx.data["field_confidence"] = {
            item.document_id: item.confidence for item in extracted
        }
        ctx.data["validation_warnings"] = {
            item.document_id: item.validation_warnings for item in extracted
        }

        return StepResult(
            output={
                "row_count": len(rows),
                "fields": fields,
                "documents_with_warnings": sum(
                    1 for item in extracted if item.validation_warnings
                ),
            }
        )


register_agent(
    "transform.field_extractor",
    name="Field Extractor",
    description=(
        "Use an LLM to extract structured fields from document text "
        "based on the user's task."
    ),
    example_config={
        "fields": ["vendor", "invoice_number", "amount", "date"],
        "instructions": "Amounts are in INR",
    },
    handler=FieldExtractorHandler(),
)
