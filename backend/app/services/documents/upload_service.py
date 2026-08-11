"""
Upload Service — orchestrates the full upload + extraction pipeline.
"""

import logging
import time
import uuid

from fastapi import UploadFile

from app.config import settings
from app.models.api.upload import UploadResponse, UploadedDocument
from app.models.domain.document import InvalidUploadError
from app.models.domain.upload import UploadRecord
from app.persistence.protocols import DataRepository, DocumentStorageRepository
from app.services.documents.text_extractor import ExtractionResult, extract_text
from app.services.usage.page_count import (
    assert_within_page_limit,
    count_pages_from_bytes,
)

logger = logging.getLogger("upload")

MAX_FILES_PER_UPLOAD = 10


class UploadService:
    def __init__(
        self,
        store: DocumentStorageRepository,
        repo: DataRepository,
    ) -> None:
        self._store = store
        self._repo = repo

    async def process_upload_batch(
        self,
        files: list[UploadFile],
        *,
        user_id: str,
    ) -> UploadResponse:
        """Process a batch of uploaded files end-to-end and bind to owner."""
        self._validate_batch(files)
        await self._validate_page_limits(files)

        upload_id = str(uuid.uuid4())
        logger.info(
            "Upload batch started — %d file(s), upload_id=%s user=%s",
            len(files),
            upload_id,
            user_id,
        )

        documents: list[UploadedDocument] = []
        for file in files:
            documents.append(await self._process_single_file(file, upload_id))

        self._repo.save_upload(UploadRecord(upload_id=upload_id, user_id=user_id))

        return UploadResponse(
            upload_id=upload_id,
            documents=documents,
            message=f"Processed {len(documents)} document(s)",
        )

    def _validate_batch(self, files: list[UploadFile]) -> None:
        if not files:
            raise InvalidUploadError("At least one file is required")
        if len(files) > MAX_FILES_PER_UPLOAD:
            raise InvalidUploadError(f"Maximum {MAX_FILES_PER_UPLOAD} files per upload")

        total_bytes = 0
        max_total_bytes = settings.max_upload_size_bytes * MAX_FILES_PER_UPLOAD
        for file in files:
            if file.size is not None and file.size > settings.max_upload_size_bytes:
                raise InvalidUploadError(
                    f"File '{file.filename}' exceeds the "
                    f"{settings.max_upload_size_mb} MB per-file limit"
                )
            if file.size is not None:
                total_bytes += file.size

        if total_bytes > max_total_bytes:
            raise InvalidUploadError(
                f"Total upload size exceeds "
                f"{settings.max_upload_size_mb * MAX_FILES_PER_UPLOAD} MB"
            )

    async def _validate_page_limits(self, files: list[UploadFile]) -> None:
        """Reject any file over max_pages_per_file before storage/OCR spend."""
        for file in files:
            data = await file.read()
            await file.seek(0)
            name = file.filename or "document"
            pages = count_pages_from_bytes(name, data)
            assert_within_page_limit(name, pages)

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
