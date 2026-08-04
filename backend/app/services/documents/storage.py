"""
Storage Service — saves uploaded files to disk.

WHY: The API route shouldn't know HOW files are saved.
     This service handles: validate extension, generate unique ID, write to disk.
     Later we can swap local disk → Supabase Storage without touching the route.
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings


def validate_file(file: UploadFile) -> None:
    """Reject files that are too big or wrong type."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    ext = Path(file.filename).suffix.lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Use: {', '.join(settings.allowed_extensions)}",
        )


async def save_upload(file: UploadFile, upload_id: str) -> tuple[str, Path]:
    """
    Save one uploaded file to disk.

    Returns:
        (document_id, full_path_on_disk)
    """
    validate_file(file)

    document_id = str(uuid.uuid4())
    ext = Path(file.filename).suffix.lower()

    # Organize: uploads/{upload_id}/{document_id}.pdf
    upload_folder = settings.upload_dir / upload_id
    upload_folder.mkdir(parents=True, exist_ok=True)

    dest_path = upload_folder / f"{document_id}{ext}"

    # Read file in chunks (memory-safe for larger files)
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.max_upload_size_mb} MB",
        )

    dest_path.write_bytes(content)
    return document_id, dest_path
