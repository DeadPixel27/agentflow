from pydantic import BaseModel, Field

from app.models.api.users import UserResponse


class SignInRequest(BaseModel):
    name: str = Field(min_length=1)
    email: str = Field(min_length=3)


class SignInResponse(BaseModel):
    user: UserResponse
    is_new_user: bool
    auth_provider: str
    token: str
