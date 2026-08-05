"""Auth provider interface — implementations in separate files per backend."""

from typing import Protocol

from app.models.domain.user import UserRecord


class AuthProvider(Protocol):
    """Sign-in / registration contract."""

    @property
    def provider_name(self) -> str:
        """e.g. 'email'."""

    def sign_in_or_register(self, name: str, email: str) -> tuple[UserRecord, bool]:
        """
        Return (user, is_new_user).
        Existing users are matched by normalized email.
        """
