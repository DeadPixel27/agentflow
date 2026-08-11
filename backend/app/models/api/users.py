from typing import Optional

from pydantic import BaseModel, Field, field_validator


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    email: str = ""


class UserUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Name is required")
        return cleaned


class UserResponse(BaseModel):
    user_id: str
    name: str
    email: str
    created_at: Optional[str] = None
