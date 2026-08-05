"""Upload batch metadata and document file serving."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.api.dependencies import DocStoreDep
from app.models.api.upload import UploadDocumentsResponse, UploadedDocumentSummary
from app.models.domain.document import DocumentNotFoundError, UploadNotFoundError
from app.persistence.documents.validation import media_type_for

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.get("/{upload_id}", response_model=UploadDocumentsResponse)
async def get_upload_documents(upload_id: str, store: DocStoreDep) -> UploadDocumentsResponse:
    """List documents in an upload batch (no extracted text)."""
    try:
        metadata = await store.list_documents(upload_id)
    except UploadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return UploadDocumentsResponse(
        upload_id=upload_id,
        documents=[
            UploadedDocumentSummary(
                document_id=doc.document_id,
                filename=doc.filename,
                file_type=doc.file_type,
            )
            for doc in metadata
        ],
    )


@router.get("/{upload_id}/documents/{document_id}")
async def get_upload_document_file(
    upload_id: str,
    document_id: str,
    store: DocStoreDep,
) -> Response:
    """Download or preview an uploaded input document."""
    try:
        metadata = await store.list_documents(upload_id)
        doc = next((d for d in metadata if d.document_id == document_id), None)
        if doc is None:
            raise DocumentNotFoundError(
                f"Document not found: {document_id} in upload {upload_id}"
            )
        content = await store.read_bytes(upload_id, document_id)
    except UploadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(
        content=content,
        media_type=media_type_for(doc.file_type),
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )
