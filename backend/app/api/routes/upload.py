"""
Upload Route — thin HTTP controller.

JOB: Receive the HTTP request, delegate to upload_service, return the response.
     No business logic here — just HTTP concerns.
"""

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.api.dependencies import UploadServiceDep
from app.config import settings
from app.models.api.upload import UploadResponse
from app.models.domain.document import InvalidUploadError
from app.rate_limit import limiter

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
@limiter.limit(settings.rate_limit_upload)
async def upload_documents(
    request: Request,
    upload_service: UploadServiceDep,
    files: list[UploadFile] = File(..., description="1-10 PDF or image files"),
) -> UploadResponse:
    try:
        return await upload_service.process_upload_batch(files)
    except InvalidUploadError as e:
        raise HTTPException(status_code=400, detail=str(e))
