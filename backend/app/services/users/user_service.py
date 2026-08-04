"""User service — create and fetch users."""

import uuid

from app.models.domain.user import UserRecord
from app.persistence.store import get_user, list_users, save_user


class UserNotFoundError(Exception):
    pass


def create_user(name: str, *, email: str = "") -> UserRecord:
    user = UserRecord(
        user_id=str(uuid.uuid4()),
        name=name.strip(),
        email=email.strip(),
    )
    save_user(user)
    return user


def fetch_user(user_id: str) -> UserRecord:
    user = get_user(user_id)
    if user is None:
        raise UserNotFoundError(f"User not found: {user_id}")
    return user


def fetch_all_users() -> list[UserRecord]:
    return list_users()


def require_user(user_id: str) -> UserRecord:
    return fetch_user(user_id)
