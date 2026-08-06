"""Shared upload validation rules."""

from pathlib import Path

import filetype
from fastapi import UploadFile

from app.config import settings
from app.models.domain.document import InvalidUploadError

_ALLOWED_MIME_BY_EXT: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
}


def validate_file_size(content: bytes) -> None:
    """Reject empty files or files over the configured per-file limit."""
    if not content:
        raise InvalidUploadError("Empty file")
    if len(content) > settings.max_upload_size_bytes:
        raise InvalidUploadError(
            f"File too large. Max size: {settings.max_upload_size_mb} MB per file"
        )


def validate_upload_file(file: UploadFile) -> None:
    """Reject files with missing names or disallowed extensions."""
    if not file.filename:
        raise InvalidUploadError("Filename is required")

    ext = Path(file.filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise InvalidUploadError(
            f"File type '{ext}' not allowed. "
            f"Use: {', '.join(sorted(settings.allowed_extensions))}"
        )


def validate_file_content(content: bytes, ext: str) -> None:
    """Verify file size and that bytes match the declared extension."""
    validate_file_size(content)

    allowed_mimes = _ALLOWED_MIME_BY_EXT.get(ext)
    if not allowed_mimes:
        raise InvalidUploadError(f"Unsupported file extension: {ext}")

    if ext == ".pdf" and content.startswith(b"%PDF"):
        return

    detected = filetype.guess(content)
    if detected is None or detected.mime not in allowed_mimes:
        raise InvalidUploadError(
            f"File content does not match extension '{ext}'. "
            "Upload a valid PDF or image file."
        )


def media_type_for(file_type: str) -> str:
    return {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(file_type.lower(), "application/octet-stream")
