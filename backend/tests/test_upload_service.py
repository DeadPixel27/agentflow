"""Tests for upload service batch validation."""

import io

import fitz
import pytest
from fastapi import UploadFile

from app.config import settings
from app.models.domain.document import InvalidUploadError
from app.persistence.memory_repository import MemoryRepository
from app.services.documents.upload_service import UploadService


class _StubDocumentStore:
    backend_name = "stub"

    async def save_document(self, upload_id: str, file: UploadFile):
        raise AssertionError("save_document should not be called when batch validation fails")


def _StubRepo():
    return MemoryRepository()


def _file_with_size(name: str, size: int) -> UploadFile:
    upload = UploadFile(filename=name, file=io.BytesIO(b"x"))
    upload.size = size
    return upload


def _pdf_upload(name: str, pages: int) -> UploadFile:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page()
    data = doc.tobytes()
    doc.close()
    upload = UploadFile(filename=name, file=io.BytesIO(data))
    upload.size = len(data)
    return upload


@pytest.mark.asyncio
async def test_rejects_empty_batch():
    service = UploadService(_StubDocumentStore(), _StubRepo())
    with pytest.raises(InvalidUploadError, match="At least one file"):
        await service.process_upload_batch([], user_id="user-1")


@pytest.mark.asyncio
async def test_rejects_file_over_per_file_limit():
    service = UploadService(_StubDocumentStore(), _StubRepo())
    oversized = _file_with_size("huge.pdf", settings.max_upload_size_bytes + 1)
    with pytest.raises(InvalidUploadError, match="per-file limit"):
        await service.process_upload_batch([oversized], user_id="user-1")


@pytest.mark.asyncio
async def test_rejects_too_many_files():
    service = UploadService(_StubDocumentStore(), _StubRepo())
    files = [_file_with_size(f"doc-{i}.pdf", 1024) for i in range(11)]
    with pytest.raises(InvalidUploadError, match="Maximum 10 files"):
        await service.process_upload_batch(files, user_id="user-1")


@pytest.mark.asyncio
async def test_rejects_pdf_over_max_pages(monkeypatch):
    monkeypatch.setattr(settings, "max_pages_per_file", 10)
    service = UploadService(_StubDocumentStore(), _StubRepo())
    too_long = _pdf_upload("long.pdf", 11)
    with pytest.raises(InvalidUploadError, match="11 pages"):
        await service.process_upload_batch([too_long], user_id="user-1")


@pytest.mark.asyncio
async def test_allows_pdf_at_max_pages(monkeypatch):
    """Page validation passes at the limit; stub store proves we got past it."""
    monkeypatch.setattr(settings, "max_pages_per_file", 10)

    class _CountingStore(_StubDocumentStore):
        def __init__(self) -> None:
            self.calls = 0

        async def save_document(self, upload_id: str, file: UploadFile):
            self.calls += 1
            raise AssertionError("stop after page validation")

    store = _CountingStore()
    service = UploadService(store, _StubRepo())
    ok = _pdf_upload("ok.pdf", 10)
    with pytest.raises(AssertionError, match="stop after page validation"):
        await service.process_upload_batch([ok], user_id="user-1")
    assert store.calls == 1
