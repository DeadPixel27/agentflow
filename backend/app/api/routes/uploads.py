"""Upload batch metadata and document file serving."""

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.api.dependencies import CurrentUserDep, DocStoreDep, DocumentFileUserDep, RepoDep
from app.api.ownership import get_owned_upload
from app.models.api.upload import (
    DocumentAccessResponse,
    UploadDocumentsResponse,
    UploadedDocumentSummary,
)
from app.models.domain.document import DocumentNotFoundError, UploadNotFoundError
from app.persistence.documents.validation import media_type_for
from app.services.auth.jwt import create_document_access_token

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.get("/{upload_id}", response_model=UploadDocumentsResponse)
async def get_upload_documents(
    upload_id: str,
    store: DocStoreDep,
    repo: RepoDep,
    current_user: CurrentUserDep,
) -> UploadDocumentsResponse:
    """List documents in an upload batch (no extracted text)."""
    get_owned_upload(repo, upload_id, current_user)
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


@router.post(
    "/{upload_id}/documents/{document_id}/access",
    response_model=DocumentAccessResponse,
)
async def mint_document_access(
    request: Request,
    upload_id: str,
    document_id: str,
    store: DocStoreDep,
    repo: RepoDep,
    current_user: CurrentUserDep,
) -> DocumentAccessResponse:
    """Mint a short-lived URL for <img>/<iframe>/open-in-new-tab (Bearer required)."""
    get_owned_upload(repo, upload_id, current_user)
    try:
        metadata = await store.list_documents(upload_id)
        doc = next((d for d in metadata if d.document_id == document_id), None)
        if doc is None:
            raise DocumentNotFoundError(
                f"Document not found: {document_id} in upload {upload_id}"
            )
    except UploadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DocumentNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    token, expires_at = create_document_access_token(
        current_user.user_id,
        upload_id,
        document_id,
    )
    base = str(request.base_url).rstrip("/")
    url = (
        f"{base}/api/uploads/{quote(upload_id, safe='')}"
        f"/documents/{quote(document_id, safe='')}"
        f"?doc_token={quote(token, safe='')}"
    )
    return DocumentAccessResponse(url=url, expires_at=expires_at.isoformat())


@router.get("/{upload_id}/documents/{document_id}")
async def get_upload_document_file(
    upload_id: str,
    document_id: str,
    store: DocStoreDep,
    repo: RepoDep,
    current_user: DocumentFileUserDep,
) -> Response:
    """Download or preview an uploaded input document (Bearer or ?doc_token=)."""
    get_owned_upload(repo, upload_id, current_user)
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
