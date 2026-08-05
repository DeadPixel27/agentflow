"""Auth service — HTTP-facing sign-in / registration."""

from app.models.domain.user import UserRecord
from app.persistence.protocols import DataRepository
from app.services.auth.registry import get_auth_provider


class AuthService:
    def __init__(self, repo: DataRepository) -> None:
        self._repo = repo
        self._provider = get_auth_provider(repo)

    def sign_in_or_register(self, name: str, email: str) -> tuple[UserRecord, bool]:
        return self._provider.sign_in_or_register(name, email)

    @property
    def provider_name(self) -> str:
        return self._provider.provider_name
