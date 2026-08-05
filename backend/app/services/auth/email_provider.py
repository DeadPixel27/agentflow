"""Email-based auth — lookup user by email in the data repository (no password)."""

import uuid

from app.models.domain.user import UserRecord
from app.persistence.protocols import DataRepository


def normalize_email(email: str) -> str:
    return email.strip().lower()


class EmailAuthProvider:
    """Match users by email; create if not found. Future: swap for Supabase Auth."""

    provider_name = "email"

    def __init__(self, repo: DataRepository) -> None:
        self._repo = repo

    def sign_in_or_register(self, name: str, email: str) -> tuple[UserRecord, bool]:
        normalized = normalize_email(email)
        if not normalized:
            raise ValueError("Email is required to sign in")

        existing = self._repo.get_user_by_email(normalized)
        if existing is not None:
            if name.strip() and name.strip() != existing.name:
                updated = UserRecord(
                    user_id=existing.user_id,
                    name=name.strip(),
                    email=existing.email,
                    created_at=existing.created_at,
                )
                self._repo.save_user(updated)
                return updated, False
            return existing, False

        user = UserRecord(
            user_id=str(uuid.uuid4()),
            name=name.strip(),
            email=normalized,
        )
        self._repo.save_user(user)
        return user, True
