"""User service — create and fetch users."""

import uuid

from app.models.domain.user import UserRecord
from app.persistence.protocols import DataRepository


class UserNotFoundError(Exception):
    pass


class UserService:
    def __init__(self, repo: DataRepository) -> None:
        self._repo = repo

    def create_user(self, name: str, *, email: str = "") -> UserRecord:
        user = UserRecord(
            user_id=str(uuid.uuid4()),
            name=name.strip(),
            email=email.strip(),
        )
        self._repo.save_user(user)
        return user

    def fetch_user(self, user_id: str) -> UserRecord:
        user = self._repo.get_user(user_id)
        if user is None:
            raise UserNotFoundError(f"User not found: {user_id}")
        return user

    def update_name(self, user_id: str, name: str) -> UserRecord:
        user = self.fetch_user(user_id)
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("Name is required")
        if cleaned == user.name:
            return user
        updated = UserRecord(
            user_id=user.user_id,
            name=cleaned,
            email=user.email,
            created_at=user.created_at,
        )
        self._repo.save_user(updated)
        return updated

    def fetch_all_users(self) -> list[UserRecord]:
        return self._repo.list_users()

    def require_user(self, user_id: str) -> UserRecord:
        return self.fetch_user(user_id)
