"""Email API request/response models."""

from pydantic import BaseModel, EmailStr, Field


class EmailResultsRequest(BaseModel):
    to_email: EmailStr = Field(validation_alias="to")
    subject: str = "Your AgentFlow Results"

    model_config = {"populate_by_name": True}


class EmailResultsResponse(BaseModel):
    status: str
    email_id: str
    message: str
