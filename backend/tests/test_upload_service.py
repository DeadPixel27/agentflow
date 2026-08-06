"""Tests for upload service batch validation."""

import io

import pytest
from fastapi import UploadFile

from app.config import settings
from app.models.domain.document import InvalidUploadError
from app.services.documents.upload_service import UploadService


class _StubDocumentStore:
    backend_name = "stub"

    async def save_document(self, upload_id: str, file: UploadFile):
        raise AssertionError("save_document should not be called when batch validation fails")


def _file_with_size(name: str, size: int) -> UploadFile:
    upload = UploadFile(filename=name, file=io.BytesIO(b"x"))
    upload.size = size
    return upload


@pytest.mark.asyncio
async def test_rejects_empty_batch():
    service = UploadService(_StubDocumentStore())
    with pytest.raises(InvalidUploadError, match="At least one file"):
        await service.process_upload_batch([])


@pytest.mark.asyncio
async def test_rejects_file_over_per_file_limit():
    service = UploadService(_StubDocumentStore())
    oversized = _file_with_size("huge.pdf", settings.max_upload_size_bytes + 1)
    with pytest.raises(InvalidUploadError, match="per-file limit"):
        await service.process_upload_batch([oversized])


@pytest.mark.asyncio
async def test_rejects_too_many_files():
    service = UploadService(_StubDocumentStore())
    files = [_file_with_size(f"doc-{i}.pdf", 1024) for i in range(11)]
    with pytest.raises(InvalidUploadError, match="Maximum 10 files"):
        await service.process_upload_batch(files)
