from typing import Optional

from pydantic import BaseModel, Field


class UploadedDocument(BaseModel):
    document_id: str
    filename: str
    file_type: str
    storage_path: str
    extracted_text: str = ""
    extraction_method: str = ""
    error_message: Optional[str] = None


class UploadResponse(BaseModel):
    upload_id: str = Field(description="Unique ID for this batch of uploads")
    documents: list[UploadedDocument]
    message: str = "Upload successful"


class UploadedDocumentSummary(BaseModel):
    document_id: str
    filename: str
    file_type: str


class UploadDocumentsResponse(BaseModel):
    upload_id: str
    documents: list[UploadedDocumentSummary]


class DocumentAccessResponse(BaseModel):
    url: str = Field(description="Short-lived URL with scoped doc_token query param")
    expires_at: str = Field(description="ISO-8601 UTC expiry of the document token")

