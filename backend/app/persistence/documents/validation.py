"""Shared upload validation rules."""

from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings


def validate_upload_file(file: UploadFile) -> None:
    """Reject files that are too big or wrong type."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = Path(file.filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File type '{ext}' not allowed. "
                f"Use: {', '.join(sorted(settings.allowed_extensions))}"
            ),
        )


def media_type_for(file_type: str) -> str:
    return {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(file_type.lower(), "application/octet-stream")
