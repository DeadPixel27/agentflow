"""Google Sheets API request/response models."""

from pydantic import BaseModel, Field


class SheetsPushRequest(BaseModel):
    spreadsheet_url: str = Field(validation_alias="url")
    sheet_name: str = "AgentFlow Results"

    model_config = {"populate_by_name": True}


class SheetsPushResponse(BaseModel):
    status: str
    spreadsheet_id: str
    sheet_name: str
    rows_written: int
