"""Tests for local document storage repository."""

import io
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.config import settings
from app.models.domain.document import DocumentNotFoundError, UploadNotFoundError
from app.persistence.documents.local_repository import LocalDocumentRepository


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", tmp_path)
    return LocalDocumentRepository()


def _upload_file(name: str, content: bytes = b"%PDF-1.4 test") -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(content))


@pytest.mark.asyncio
async def test_save_list_and_read(store):
    upload_id = "batch-1"
    saved = await store.save_document(upload_id, _upload_file("invoice.pdf"))

    assert saved.document_id
    assert saved.file_type == ".pdf"
    assert saved.storage_key.startswith("batch-1/")
    # Storage object keeps uuid name
    assert saved.filename == f"{saved.document_id}.pdf"

    docs = await store.list_documents(upload_id)
    assert len(docs) == 1
    assert docs[0].document_id == saved.document_id
    assert docs[0].filename == "invoice.pdf"

    data = await store.read_bytes(upload_id, saved.document_id)
    assert data.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_list_skips_manifest_and_keeps_original_names(store):
    upload_id = "batch-names"
    a = await store.save_document(upload_id, _upload_file("Alpha Invoice.pdf"))
    b = await store.save_document(upload_id, _upload_file("receipt.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16))

    docs = await store.list_documents(upload_id)
    by_id = {doc.document_id: doc.filename for doc in docs}
    assert by_id[a.document_id] == "Alpha Invoice.pdf"
    assert by_id[b.document_id] == "receipt.png"
    assert all(doc.filename != "manifest.json" for doc in docs)


@pytest.mark.asyncio
async def test_materialize_path(store):
    upload_id = "batch-2"
    saved = await store.save_document(upload_id, _upload_file("scan.png", b"\x89PNG\r\n\x1a\n" + b"\x00" * 16))

    path = await store.materialize_path(upload_id, saved.document_id)
    assert path.exists()
    assert path.suffix == ".png"
    store.release_path(path)


@pytest.mark.asyncio
async def test_upload_not_found(store):
    with pytest.raises(UploadNotFoundError):
        await store.list_documents("missing")


@pytest.mark.asyncio
async def test_document_not_found(store):
    upload_id = "batch-3"
    await store.save_document(upload_id, _upload_file("a.pdf"))

    with pytest.raises(DocumentNotFoundError):
        await store.read_bytes(upload_id, "nonexistent-id")
