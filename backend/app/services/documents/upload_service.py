"""
Upload Service — orchestrates the full upload + extraction pipeline.

WHY this exists:
  The route (upload.py) should only handle HTTP — receive request, return response.
  All business decisions live here: validation, looping, calling other services,
  building the result.

  Later when we add a CLI or background job that processes uploads,
  it can call this same service without going through HTTP.
"""

import logging
import time
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.models.api.upload import UploadResponse, UploadedDocument
from app.services.documents.storage import save_upload
from app.services.documents.text_extractor import ExtractionResult, extract_text

logger = logging.getLogger("upload")

MAX_FILES_PER_UPLOAD = 10


class UploadValidationError(Exception):
    """Raised when upload batch fails business-rule validation."""


async def process_upload_batch(files: list[UploadFile]) -> UploadResponse:
    """
    Process a batch of uploaded files end-to-end.

    1. Validate batch size
    2. For each file: save → extract text
    3. Return structured response
    """
    _validate_batch(files)

    upload_id = str(uuid.uuid4())
    logger.info("Upload batch started — %d file(s), upload_id=%s", len(files), upload_id)

    documents: list[UploadedDocument] = []
    for file in files:
        documents.append(await _process_single_file(file, upload_id))

    return UploadResponse(
        upload_id=upload_id,
        documents=documents,
        message=f"Processed {len(documents)} document(s)",
    )


def _validate_batch(files: list[UploadFile]) -> None:
    if not files:
        raise UploadValidationError("At least one file is required")
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise UploadValidationError(f"Maximum {MAX_FILES_PER_UPLOAD} files per upload")


async def _process_single_file(file: UploadFile, upload_id: str) -> UploadedDocument:
    """Save one file and extract its text."""
    t0 = time.perf_counter()

    document_id, saved_path = await save_upload(file, upload_id)
    logger.info("Saved %s → %s", file.filename, saved_path.name)

    result = await extract_text(saved_path)
    elapsed = time.perf_counter() - t0

    if result.error_message:
        logger.error("Extraction failed for %s: %s", file.filename, result.error_message)
    else:
        logger.info(
            "Extracted %s via %s in %.1fs (%d chars)",
            file.filename,
            result.method,
            elapsed,
            len(result.text),
        )

    return _build_document(file, document_id, saved_path, result)


def _build_document(
    file: UploadFile,
    document_id: str,
    saved_path: Path,
    result: ExtractionResult,
) -> UploadedDocument:
    return UploadedDocument(
        document_id=document_id,
        filename=file.filename or "unknown",
        file_type=saved_path.suffix.lower(),
        storage_path=str(saved_path),
        extracted_text=result.text,
        extraction_method=result.method,
        error_message=result.error_message,
    )
