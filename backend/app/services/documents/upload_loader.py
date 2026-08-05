"""
Upload loader — read documents from a prior upload batch.

Shared by the planner (metadata + text preview) and field extractor (full text).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.models.domain.document import UploadNotFoundError
from app.persistence import get_document_store
from app.services.documents.text_extractor import extract_text

# Re-export for existing imports
__all__ = ["UploadDocumentInfo", "UploadNotFoundError", "load_upload_documents"]


@dataclass
class UploadDocumentInfo:
    document_id: str
    filename: str
    file_type: str
    extraction_method: str
    text: str
    storage_key: str
    upload_id: str
    error_message: Optional[str] = None

    @property
    def text_preview(self) -> str:
        return self.text[:500]

    @property
    def has_text(self) -> bool:
        return bool(self.text.strip()) and not self.error_message


async def load_upload_documents(upload_id: str) -> list[UploadDocumentInfo]:
    """Load all files from an upload batch and extract their text."""
    store = get_document_store()
    if not await store.upload_exists(upload_id):
        raise UploadNotFoundError(f"Upload not found: {upload_id}")

    metadata_list = await store.list_documents(upload_id)
    documents: list[UploadDocumentInfo] = []

    for meta in metadata_list:
        path = await store.materialize_path(upload_id, meta.document_id)
        try:
            result = await extract_text(path)
        finally:
            store.release_path(path)

        documents.append(
            UploadDocumentInfo(
                document_id=meta.document_id,
                filename=meta.filename,
                file_type=meta.file_type,
                extraction_method=result.method,
                text=result.text,
                storage_key=meta.storage_key,
                upload_id=upload_id,
                error_message=result.error_message,
            )
        )

    return documents
