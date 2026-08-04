"""OCR for images and scanned PDFs (Tesseract)."""

import asyncio
from pathlib import Path
from typing import Any

from app.agents.core.base import StepHandler, StepResult
from app.agents.core.context import WorkflowContext
from app.agents.core.registry import register_agent
from app.services.documents.text_extractor import extract_text_from_image, extract_text_from_pdf


class OcrHandler(StepHandler):
    async def execute(
        self,
        ctx: WorkflowContext,
        config: dict[str, Any],
    ) -> StepResult:
        documents = ctx.data.get("documents", [])
        image_types = {".png", ".jpg", ".jpeg"}
        updated = 0

        for doc in documents:
            needs_ocr = (
                doc.get("file_type") in image_types
                or doc.get("extraction_method") == "tesseract"
                or not doc.get("text", "").strip()
            )
            if not needs_ocr:
                continue

            file_path = Path(doc["file_path"])
            if doc.get("file_type") == ".pdf":
                text, method = await asyncio.to_thread(extract_text_from_pdf, file_path)
            else:
                text, method = await asyncio.to_thread(extract_text_from_image, file_path)

            doc["text"] = text
            doc["extraction_method"] = method
            updated += 1

        ctx.data["documents"] = documents
        return StepResult(output={"documents_updated": updated})


register_agent(
    "processor.ocr",
    name="OCR Agent",
    description=(
        "Convert scanned images or scanned PDFs to text using Tesseract OCR. "
        "Use when documents are photos, screenshots, or PDFs without embedded text."
    ),
    example_config={},
    handler=OcrHandler(),
)
