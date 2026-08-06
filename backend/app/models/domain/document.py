"""Document storage domain models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoredDocument:
    """A document saved to storage."""

    document_id: str
    filename: str
    file_type: str
    storage_key: str


@dataclass(frozen=True)
class DocumentMetadata:
    """Document listing entry (no file bytes)."""

    document_id: str
    filename: str
    file_type: str
    storage_key: str


class UploadNotFoundError(Exception):
    """Raised when an upload batch does not exist in storage."""


class DocumentNotFoundError(Exception):
    """Raised when a document is not found within an upload batch."""


class InvalidUploadError(Exception):
    """Raised when an upload fails validation (type, size, or content)."""
