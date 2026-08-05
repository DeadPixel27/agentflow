"""Workflow context — shared state passed between step handlers."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowContext:
    upload_id: str
    task_description: str = ""
    data: dict[str, Any] = field(default_factory=dict)


def documents_to_dicts(documents: list) -> list[dict[str, Any]]:
    """Convert UploadDocumentInfo objects to plain dicts for ctx.data."""
    return [
        {
            "document_id": doc.document_id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "text": doc.text,
            "extraction_method": doc.extraction_method,
            "storage_key": doc.storage_key,
        }
        for doc in documents
    ]
