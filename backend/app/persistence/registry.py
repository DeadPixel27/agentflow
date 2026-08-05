"""
Backend registry — the ONLY file that maps config → implementation.

To add a new backend (e.g. S3, DynamoDB):
  1. Create one file implementing the Protocol (e.g. persistence/documents/s3_repository.py)
  2. Register it in the dict below
  3. Set the env var (e.g. DOCUMENT_STORAGE=s3)

No other files need to change.
"""

import logging
from typing import TypeVar

from typing import Optional

from app.config import settings
from app.persistence.documents.local_repository import LocalDocumentRepository
from app.persistence.documents.supabase_repository import SupabaseDocumentRepository
from app.persistence.memory_repository import MemoryRepository
from app.persistence.protocols import DataRepository, DocumentStorageRepository
from app.persistence.supabase_repository import SupabaseRepository, is_supabase_configured

logger = logging.getLogger("persistence")

T = TypeVar("T")

# Register data backends here — add new ones without touching callers
_DATA_BACKENDS: dict[str, type[DataRepository]] = {
    "memory": MemoryRepository,
    "supabase": SupabaseRepository,
}

# Register document storage backends here
_DOCUMENT_BACKENDS: dict[str, type[DocumentStorageRepository]] = {
    "local": LocalDocumentRepository,
    "supabase": SupabaseDocumentRepository,
    # "s3": S3DocumentRepository,  # future: one file + one line here
}

_data_instance: Optional[DataRepository] = None
_document_instance: Optional[DocumentStorageRepository] = None


def _resolve_data_backend() -> str:
    mode = settings.persistence_backend.lower()
    if mode == "auto":
        return "supabase" if is_supabase_configured() else "memory"
    if mode not in _DATA_BACKENDS:
        logger.warning("Unknown PERSISTENCE_BACKEND=%s — using memory", mode)
        return "memory"
    if mode == "supabase" and not is_supabase_configured():
        logger.warning("PERSISTENCE_BACKEND=supabase but not configured — using memory")
        return "memory"
    return mode


def _resolve_document_backend() -> str:
    mode = settings.document_storage.lower()
    if mode == "auto":
        return "supabase" if is_supabase_configured() else "local"
    if mode not in _DOCUMENT_BACKENDS:
        logger.warning("Unknown DOCUMENT_STORAGE=%s — using local", mode)
        return "local"
    if mode == "supabase" and not is_supabase_configured():
        logger.warning("DOCUMENT_STORAGE=supabase but not configured — using local")
        return "local"
    return mode


def get_repository() -> DataRepository:
    """Return the configured data repository (users, workflows, runs)."""
    global _data_instance
    backend = _resolve_data_backend()
    if _data_instance is None or _data_instance.backend_name != backend:
        _data_instance = _DATA_BACKENDS[backend]()
    return _data_instance


def get_document_store() -> DocumentStorageRepository:
    """Return the configured document file storage."""
    global _document_instance
    backend = _resolve_document_backend()
    if _document_instance is None or _document_instance.backend_name != backend:
        _document_instance = _DOCUMENT_BACKENDS[backend]()
    return _document_instance


def get_data_backend_name() -> str:
    return _resolve_data_backend()


def get_document_backend_name() -> str:
    return _resolve_document_backend()
