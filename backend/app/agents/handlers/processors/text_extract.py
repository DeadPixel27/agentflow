"""Extract embedded text from digital PDFs (PyMuPDF)."""

import asyncio
from typing import Any

from app.agents.core.base import StepHandler, StepResult
from app.agents.core.context import WorkflowContext
from app.agents.core.registry import register_agent
from app.persistence import get_document_store
from app.services.documents.text_extractor import extract_text_from_pdf


class TextExtractHandler(StepHandler):
    async def execute(
        self,
        ctx: WorkflowContext,
        config: dict[str, Any],
    ) -> StepResult:
        documents = ctx.data.get("documents", [])
        store = get_document_store()
        updated = 0

        for doc in documents:
            if doc.get("file_type") != ".pdf":
                continue
            if doc.get("text", "").strip():
                continue

            path = await store.materialize_path(ctx.upload_id, doc["document_id"])
            try:
                text, method = await asyncio.to_thread(extract_text_from_pdf, path)
            finally:
                store.release_path(path)

            doc["text"] = text
            doc["extraction_method"] = method
            updated += 1

        ctx.data["documents"] = documents
        return StepResult(output={"documents_updated": updated})


register_agent(
    "processor.text_extract",
    name="Text Extractor",
    description=(
        "Extract embedded text from digital PDFs using PyMuPDF. "
        "Use for PDFs created from Word/Excel with selectable text."
    ),
    example_config={},
    handler=TextExtractHandler(),
)
