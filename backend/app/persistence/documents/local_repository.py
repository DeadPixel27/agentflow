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
from app.persistence.documents.manifest import (
    MANIFEST_FILENAME,
    empty_manifest,
    is_manifest_filename,
    manifest_to_bytes,
    original_filenames_map,
    parse_manifest,
    upsert_manifest_entry,
)
from app.persistence.documents.validation import validate_file_content, validate_upload_file


class LocalDocumentRepository:
    backend_name = "local"

    def _upload_dir(self, upload_id: str) -> Path:
        return settings.upload_dir / upload_id

    def _manifest_path(self, upload_id: str) -> Path:
        return self._upload_dir(upload_id) / MANIFEST_FILENAME

    def _read_manifest(self, upload_id: str) -> dict:
        path = self._manifest_path(upload_id)
        if not path.is_file():
            return empty_manifest()
        return parse_manifest(path.read_bytes())

    def _write_manifest(self, upload_id: str, manifest: dict) -> None:
        upload_folder = self._upload_dir(upload_id)
        upload_folder.mkdir(parents=True, exist_ok=True)
        self._manifest_path(upload_id).write_bytes(manifest_to_bytes(manifest))

    def _record_original_filename(
        self, upload_id: str, document_id: str, original_filename: str
    ) -> None:
        if not original_filename:
            return
        manifest = upsert_manifest_entry(
            self._read_manifest(upload_id),
            document_id,
            original_filename,
        )
        self._write_manifest(upload_id, manifest)

    def _find_document_path(self, upload_id: str, document_id: str) -> Path:
        upload_dir = self._upload_dir(upload_id)
        if not upload_dir.is_dir():
            raise UploadNotFoundError(f"Upload not found: {upload_id}")

        for file_path in upload_dir.iterdir():
            if (
                file_path.is_file()
                and not is_manifest_filename(file_path.name)
                and file_path.stem == document_id
            ):
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
        original = file.filename or dest_path.name
        self._record_original_filename(upload_id, document_id, original)
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

        names = original_filenames_map(self._read_manifest(upload_id))
        documents: list[DocumentMetadata] = []
        for file_path in sorted(upload_dir.iterdir()):
            if not file_path.is_file() or is_manifest_filename(file_path.name):
                continue
            documents.append(
                DocumentMetadata(
                    document_id=file_path.stem,
                    filename=names.get(file_path.stem, file_path.name),
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

    async def save_document_bytes(
        self,
        upload_id: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> StoredDocument:
        document_id = str(uuid.uuid4())
        ext = Path(filename).suffix.lower()
        if not ext:
            ext = ".pdf"
        upload_folder = self._upload_dir(upload_id)
        upload_folder.mkdir(parents=True, exist_ok=True)

        dest_path = upload_folder / f"{document_id}{ext}"
        validate_file_content(content, ext)

        dest_path.write_bytes(content)
        storage_key = f"{upload_id}/{document_id}{ext}"
        self._record_original_filename(upload_id, document_id, filename or dest_path.name)
        return StoredDocument(
            document_id=document_id,
            filename=dest_path.name,
            file_type=ext,
            storage_key=storage_key,
        )
