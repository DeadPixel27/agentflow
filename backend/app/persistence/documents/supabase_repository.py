"""Supabase Storage document repository — only file that talks to Supabase Storage."""

import logging
import tempfile
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
from app.persistence.documents.validation import (
    media_type_for,
    validate_file_content,
    validate_upload_file,
)
from app.persistence.supabase_repository import get_supabase_client

logger = logging.getLogger("storage")

_temp_paths: set[str] = set()


class SupabaseDocumentRepository:
    backend_name = "supabase"

    def _bucket(self) -> str:
        return settings.supabase_documents_bucket

    def _object_path(self, upload_id: str, filename: str) -> str:
        return f"{upload_id}/{filename}"

    def _read_manifest(self, upload_id: str) -> dict:
        path = self._object_path(upload_id, MANIFEST_FILENAME)
        try:
            data = get_supabase_client().storage.from_(self._bucket()).download(path)
        except Exception:
            return empty_manifest()
        return parse_manifest(data)

    def _write_manifest(self, upload_id: str, manifest: dict) -> None:
        path = self._object_path(upload_id, MANIFEST_FILENAME)
        get_supabase_client().storage.from_(self._bucket()).upload(
            path,
            manifest_to_bytes(manifest),
            file_options={
                "content-type": "application/json",
                "upsert": "true",
            },
        )

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

    async def save_document(self, upload_id: str, file: UploadFile) -> StoredDocument:
        validate_upload_file(file)

        document_id = str(uuid.uuid4())
        ext = Path(file.filename or "").suffix.lower()
        object_name = f"{document_id}{ext}"
        storage_path = self._object_path(upload_id, object_name)

        content = await file.read()
        validate_file_content(content, ext)

        get_supabase_client().storage.from_(self._bucket()).upload(
            storage_path,
            content,
            file_options={
                "content-type": media_type_for(ext),
                "upsert": "true",
            },
        )

        original = file.filename or object_name
        self._record_original_filename(upload_id, document_id, original)

        return StoredDocument(
            document_id=document_id,
            filename=object_name,
            file_type=ext,
            storage_key=storage_path,
        )

    async def list_documents(self, upload_id: str) -> list[DocumentMetadata]:
        try:
            entries = get_supabase_client().storage.from_(self._bucket()).list(upload_id)
        except Exception as e:
            logger.warning("Supabase list failed for upload %s: %s", upload_id, e)
            raise UploadNotFoundError(f"Upload not found: {upload_id}") from e

        if not entries:
            raise UploadNotFoundError(f"Upload not found: {upload_id}")

        names = original_filenames_map(self._read_manifest(upload_id))
        documents: list[DocumentMetadata] = []
        for entry in entries:
            name = entry.get("name") if isinstance(entry, dict) else getattr(entry, "name", None)
            if not name or name.startswith(".") or is_manifest_filename(name):
                continue
            path = Path(name)
            documents.append(
                DocumentMetadata(
                    document_id=path.stem,
                    filename=names.get(path.stem, name),
                    file_type=path.suffix.lower(),
                    storage_key=self._object_path(upload_id, name),
                )
            )
        return documents

    async def upload_exists(self, upload_id: str) -> bool:
        try:
            entries = get_supabase_client().storage.from_(self._bucket()).list(upload_id)
            return bool(entries)
        except Exception:
            return False

    async def _resolve_object_name(self, upload_id: str, document_id: str) -> str:
        try:
            entries = get_supabase_client().storage.from_(self._bucket()).list(upload_id)
        except Exception as e:
            raise UploadNotFoundError(f"Upload not found: {upload_id}") from e

        for entry in entries or []:
            name = entry.get("name") if isinstance(entry, dict) else getattr(entry, "name", None)
            if not name or is_manifest_filename(name):
                continue
            if Path(name).stem == document_id:
                return name
        raise DocumentNotFoundError(
            f"Document not found: {document_id} in upload {upload_id}"
        )

    async def materialize_path(self, upload_id: str, document_id: str) -> Path:
        object_name = await self._resolve_object_name(upload_id, document_id)
        storage_path = self._object_path(upload_id, object_name)
        data = get_supabase_client().storage.from_(self._bucket()).download(storage_path)

        suffix = Path(object_name).suffix
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(data)
        tmp.close()
        _temp_paths.add(tmp.name)
        return Path(tmp.name)

    def release_path(self, path: Path) -> None:
        key = str(path)
        if key in _temp_paths:
            try:
                path.unlink(missing_ok=True)
            finally:
                _temp_paths.discard(key)

    async def read_bytes(self, upload_id: str, document_id: str) -> bytes:
        object_name = await self._resolve_object_name(upload_id, document_id)
        storage_path = self._object_path(upload_id, object_name)
        return get_supabase_client().storage.from_(self._bucket()).download(storage_path)

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
        object_name = f"{document_id}{ext}"
        storage_path = self._object_path(upload_id, object_name)

        validate_file_content(content, ext)

        get_supabase_client().storage.from_(self._bucket()).upload(
            storage_path,
            content,
            file_options={
                "content-type": content_type or media_type_for(ext),
                "upsert": "true",
            },
        )

        self._record_original_filename(upload_id, document_id, filename or object_name)

        return StoredDocument(
            document_id=document_id,
            filename=object_name,
            file_type=ext,
            storage_key=storage_path,
        )
