from typing import Optional

from app.api.dependencies import get_current_user
from app.main import app
from app.models.api.users import UserResponse


def auth_user(
    *,
    user_id: str = "user-1",
    name: str = "Test User",
    email: str = "test@example.com",
) -> UserResponse:
    return UserResponse(
        user_id=user_id,
        name=name,
        email=email,
        created_at=None,
    )


def override_current_user(user: Optional[UserResponse] = None) -> None:
    current = user or auth_user()

    async def _fake_current_user() -> UserResponse:
        return current

    app.dependency_overrides[get_current_user] = _fake_current_user
