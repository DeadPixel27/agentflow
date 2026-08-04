"""
Upload loader — read documents from a prior upload batch.

Shared by the planner (metadata + text preview) and field extractor (full text).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.config import settings
from app.services.documents.text_extractor import extract_text


class UploadNotFoundError(Exception):
    """Raised when upload_id folder does not exist on disk."""


@dataclass
class UploadDocumentInfo:
    document_id: str
    filename: str
    file_type: str
    extraction_method: str
    text: str
    file_path: Path
    error_message: Optional[str] = None

    @property
    def text_preview(self) -> str:
        return self.text[:500]

    @property
    def has_text(self) -> bool:
        return bool(self.text.strip()) and not self.error_message


async def load_upload_documents(upload_id: str) -> list[UploadDocumentInfo]:
    """Load all files from an upload folder and extract their text."""
    upload_dir = settings.upload_dir / upload_id
    if not upload_dir.is_dir():
        raise UploadNotFoundError(f"Upload not found: {upload_id}")

    documents: list[UploadDocumentInfo] = []
    for file_path in sorted(upload_dir.iterdir()):
        if not file_path.is_file():
            continue

        result = await extract_text(file_path)
        documents.append(
            UploadDocumentInfo(
                document_id=file_path.stem,
                filename=file_path.name,
                file_type=file_path.suffix.lower(),
                extraction_method=result.method,
                text=result.text,
                file_path=file_path,
                error_message=result.error_message,
            )
        )

    return documents
