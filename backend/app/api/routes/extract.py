"""
Extract Route — AI field extraction from document text.
"""

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.api.extract import (
    ExtractFromUploadRequest,
    ExtractRequest,
    ExtractResponse,
    ExtractedFields,
)
from app.services.extraction.field_extractor import (
    DocumentInput,
    extract_fields,
    extract_fields_from_upload,
)
from app.services.documents.upload_loader import UploadNotFoundError

router = APIRouter(prefix="/api", tags=["extract"])


@router.post("/extract", response_model=ExtractResponse)
async def extract_from_text(body: ExtractRequest) -> ExtractResponse:
    """Extract structured fields from document text using Groq."""
    try:
        documents = [
            DocumentInput(
                document_id=doc.document_id,
                text=doc.text,
                filename=doc.filename,
            )
            for doc in body.documents
        ]
        results = await extract_fields(
            documents,
            body.fields,
            body.instructions,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return ExtractResponse(
        results=[
            ExtractedFields(
                document_id=r.document_id,
                filename=r.filename,
                fields=r.fields,
            )
            for r in results
        ],
        model=settings.groq_model,
    )


@router.post("/extract/from-upload", response_model=ExtractResponse)
async def extract_from_upload(body: ExtractFromUploadRequest) -> ExtractResponse:
    """Re-read files from a prior upload, then extract fields with Groq."""
    try:
        results = await extract_fields_from_upload(
            body.upload_id,
            body.fields,
            body.instructions,
        )
    except UploadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return ExtractResponse(
        results=[
            ExtractedFields(
                document_id=r.document_id,
                filename=r.filename,
                fields=r.fields,
            )
            for r in results
        ],
        model=settings.groq_model,
    )
