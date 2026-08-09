"""
Extract Route — AI field extraction from document text.
"""

from fastapi import APIRouter, HTTPException

from app.api.dependencies import CurrentUserDep
from app.api.usage_http import enforce_usage, record_extract_usage
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
from app.services.usage.page_count import count_upload_pages

router = APIRouter(prefix="/api", tags=["extract"])


def _to_response(results) -> ExtractResponse:
    return ExtractResponse(
        results=[
            ExtractedFields(
                document_id=r.document_id,
                filename=r.filename,
                fields=r.fields,
                confidence=r.confidence,
                validation_warnings=r.validation_warnings,
            )
            for r in results
        ],
        model=settings.openai_model,
    )


@router.post("/extract", response_model=ExtractResponse)
async def extract_from_text(
    body: ExtractRequest,
    current_user: CurrentUserDep,
) -> ExtractResponse:
    """Extract structured fields from document text using OpenAI."""
    page_count = max(len(body.documents), 1)
    await enforce_usage(current_user.user_id, page_count)
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

    await record_extract_usage(current_user.user_id, page_count=page_count)
    return _to_response(results)


@router.post("/extract/from-upload", response_model=ExtractResponse)
async def extract_from_upload(
    body: ExtractFromUploadRequest,
    current_user: CurrentUserDep,
) -> ExtractResponse:
    """Re-read files from a prior upload, then extract fields with OpenAI."""
    page_count = await count_upload_pages(body.upload_id)
    await enforce_usage(current_user.user_id, page_count)
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

    await record_extract_usage(current_user.user_id, page_count=page_count)
    return _to_response(results)
