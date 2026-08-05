"""
Upload Service — orchestrates the full upload + extraction pipeline.
"""

import logging
import time
import uuid

from fastapi import UploadFile

from app.models.api.upload import UploadResponse, UploadedDocument
from app.persistence.protocols import DocumentStorageRepository
from app.services.documents.text_extractor import ExtractionResult, extract_text

logger = logging.getLogger("upload")

MAX_FILES_PER_UPLOAD = 10


class UploadValidationError(Exception):
    """Raised when upload batch fails business-rule validation."""


class UploadService:
    def __init__(self, store: DocumentStorageRepository) -> None:
        self._store = store

    async def process_upload_batch(self, files: list[UploadFile]) -> UploadResponse:
        """Process a batch of uploaded files end-to-end."""
        self._validate_batch(files)

        upload_id = str(uuid.uuid4())
        logger.info("Upload batch started — %d file(s), upload_id=%s", len(files), upload_id)

        documents: list[UploadedDocument] = []
        for file in files:
            documents.append(await self._process_single_file(file, upload_id))

        return UploadResponse(
            upload_id=upload_id,
            documents=documents,
            message=f"Processed {len(documents)} document(s)",
        )

    def _validate_batch(self, files: list[UploadFile]) -> None:
        if not files:
            raise UploadValidationError("At least one file is required")
        if len(files) > MAX_FILES_PER_UPLOAD:
            raise UploadValidationError(f"Maximum {MAX_FILES_PER_UPLOAD} files per upload")

    async def _process_single_file(self, file: UploadFile, upload_id: str) -> UploadedDocument:
        """Save one file and extract its text."""
        t0 = time.perf_counter()

        stored = await self._store.save_document(upload_id, file)
        logger.info("Saved %s → %s [%s]", file.filename, stored.storage_key, self._store.backend_name)

        path = await self._store.materialize_path(upload_id, stored.document_id)
        try:
            result = await extract_text(path)
        finally:
            self._store.release_path(path)

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

        return self._build_document(file, stored, result)

    def _build_document(
        self,
        file: UploadFile,
        stored,
        result: ExtractionResult,
    ) -> UploadedDocument:
        return UploadedDocument(
            document_id=stored.document_id,
            filename=file.filename or stored.filename,
            file_type=stored.file_type,
            storage_path=stored.storage_key,
            extracted_text=result.text,
            extraction_method=result.method,
            error_message=result.error_message,
        )
