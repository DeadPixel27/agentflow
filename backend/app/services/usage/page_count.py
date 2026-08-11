"""
Count billable pages for an upload batch.

PDFs: PyMuPDF page count
Images: 1 page each
"""

from __future__ import annotations

import logging
from pathlib import Path

import fitz

from app.persistence import get_document_store

logger = logging.getLogger("usage")


def count_pages_from_bytes(filename: str, data: bytes) -> int:
    """Return page count for in-memory file bytes (PDF pages or 1 for images)."""
    suffix = Path(filename or "").suffix.lower()
    if suffix == ".pdf":
        try:
            doc = fitz.open(stream=data, filetype="pdf")
            try:
                return max(len(doc), 1)
            finally:
                doc.close()
        except Exception as e:
            logger.warning("Failed to count PDF pages for %s: %s", filename, e)
            return 1
    if suffix in {".png", ".jpg", ".jpeg"}:
        return 1
    return 1


def count_file_pages(file_path: Path) -> int:
    """Return page count for a single file (PDF pages or 1 for images)."""
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        try:
            doc = fitz.open(file_path)
            try:
                return max(len(doc), 1)
            finally:
                doc.close()
        except Exception as e:
            logger.warning("Failed to count PDF pages for %s: %s", file_path.name, e)
            return 1
    if suffix in {".png", ".jpg", ".jpeg"}:
        return 1
    return 1


def assert_within_page_limit(filename: str, pages: int) -> None:
    """Raise InvalidUploadError when a single file exceeds max_pages_per_file."""
    from app.config import settings
    from app.models.domain.document import InvalidUploadError

    limit = settings.max_pages_per_file
    if pages > limit:
        raise InvalidUploadError(
            f"File '{filename}' has {pages} pages. "
            f"Maximum is {limit} pages per file."
        )


async def count_upload_pages(upload_id: str) -> int:
    """
    Sum page counts across all documents in an upload.

    Falls back to 1 if the upload is empty or unreadable.
    """
    store = get_document_store()
    try:
        metadata_list = await store.list_documents(upload_id)
    except Exception as e:
        logger.warning("Failed to list documents for page count upload=%s: %s", upload_id, e)
        return 1

    if not metadata_list:
        return 1

    total = 0
    for meta in metadata_list:
        path = await store.materialize_path(upload_id, meta.document_id)
        try:
            total += count_file_pages(path)
        finally:
            store.release_path(path)

    return max(total, 1)
