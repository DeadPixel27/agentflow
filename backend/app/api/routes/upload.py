"""
Upload Route — thin HTTP controller.

JOB: Receive the HTTP request, delegate to upload_service, return the response.
     No business logic here — just HTTP concerns.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.dependencies import UploadServiceDep
from app.models.api.upload import UploadResponse
from app.services.documents.upload_service import UploadValidationError

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    upload_service: UploadServiceDep,
    files: list[UploadFile] = File(..., description="1-10 PDF or image files"),
) -> UploadResponse:
    try:
        return await upload_service.process_upload_batch(files)
    except UploadValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
