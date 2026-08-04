from typing import Any, Optional

from pydantic import BaseModel, Field


class ExtractDocumentInput(BaseModel):
    document_id: str
    text: str
    filename: str = ""


class ExtractRequest(BaseModel):
    fields: list[str] = Field(min_length=1)
    documents: list[ExtractDocumentInput] = Field(min_length=1)
    instructions: Optional[str] = None


class ExtractedFields(BaseModel):
    document_id: str
    filename: str = ""
    fields: dict[str, Any]


class ExtractResponse(BaseModel):
    results: list[ExtractedFields]
    model: str


class ExtractFromUploadRequest(BaseModel):
    upload_id: str
    fields: list[str] = Field(min_length=1)
    instructions: Optional[str] = None
