from typing import Optional

from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    email: str = ""


class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    created_at: Optional[str] = None
