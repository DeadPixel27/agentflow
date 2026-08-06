"""Local filesystem document repository."""

import uuid
from pathlib import Path

from fastapi import UploadFile

from app.config import settings
from app.models.domain.document import (
    DocumentMetadata,
    DocumentNotFoundError,
    StoredDocument,
    UploadNotFoundError,
)
from app.persistence.documents.validation import validate_file_content, validate_upload_file


class LocalDocumentRepository:
    backend_name = "local"

    def _upload_dir(self, upload_id: str) -> Path:
        return settings.upload_dir / upload_id

    def _find_document_path(self, upload_id: str, document_id: str) -> Path:
        upload_dir = self._upload_dir(upload_id)
        if not upload_dir.is_dir():
            raise UploadNotFoundError(f"Upload not found: {upload_id}")

        for file_path in upload_dir.iterdir():
            if file_path.is_file() and file_path.stem == document_id:
                return file_path

        raise DocumentNotFoundError(
            f"Document not found: {document_id} in upload {upload_id}"
        )

    async def save_document(self, upload_id: str, file: UploadFile) -> StoredDocument:
        validate_upload_file(file)

        document_id = str(uuid.uuid4())
        ext = Path(file.filename or "").suffix.lower()
        upload_folder = self._upload_dir(upload_id)
        upload_folder.mkdir(parents=True, exist_ok=True)

        dest_path = upload_folder / f"{document_id}{ext}"
        content = await file.read()
        validate_file_content(content, ext)

        dest_path.write_bytes(content)
        storage_key = f"{upload_id}/{document_id}{ext}"
        return StoredDocument(
            document_id=document_id,
            filename=dest_path.name,
            file_type=ext,
            storage_key=storage_key,
        )

    async def list_documents(self, upload_id: str) -> list[DocumentMetadata]:
        upload_dir = self._upload_dir(upload_id)
        if not upload_dir.is_dir():
            raise UploadNotFoundError(f"Upload not found: {upload_id}")

        documents: list[DocumentMetadata] = []
        for file_path in sorted(upload_dir.iterdir()):
            if not file_path.is_file():
                continue
            documents.append(
                DocumentMetadata(
                    document_id=file_path.stem,
                    filename=file_path.name,
                    file_type=file_path.suffix.lower(),
                    storage_key=f"{upload_id}/{file_path.name}",
                )
            )
        return documents

    async def upload_exists(self, upload_id: str) -> bool:
        return self._upload_dir(upload_id).is_dir()

    async def materialize_path(self, upload_id: str, document_id: str) -> Path:
        return self._find_document_path(upload_id, document_id)

    def release_path(self, path: Path) -> None:
        return None

    async def read_bytes(self, upload_id: str, document_id: str) -> bytes:
        path = self._find_document_path(upload_id, document_id)
        return path.read_bytes()
