"""Email auth provider tests."""

import pytest

from app.persistence.memory_repository import MemoryRepository
from app.services.auth.email_provider import EmailAuthProvider, normalize_email
from app.services.auth.service import AuthService


@pytest.fixture
def repo():
    return MemoryRepository()


@pytest.fixture
def auth(repo):
    return AuthService(repo)


def test_normalize_email():
    assert normalize_email("  Foo@Bar.com ") == "foo@bar.com"


def test_sign_in_creates_new_user(auth):
    user, is_new = auth.sign_in_or_register("DeadPixel27", "deadpixel27@example.com")
    assert is_new is True
    assert user.email == "deadpixel27@example.com"
    assert user.name == "DeadPixel27"


def test_sign_in_restores_existing_user_by_email(auth):
    first, _ = auth.sign_in_or_register("DeadPixel27", "deadpixel27@example.com")
    second, is_new = auth.sign_in_or_register("DeadPixel27", "deadpixel27@example.com")

    assert is_new is False
    assert second.user_id == first.user_id


def test_sign_in_email_is_case_insensitive(auth):
    first, _ = auth.sign_in_or_register("DeadPixel27", "DeadPixel27@Example.com")
    second, is_new = auth.sign_in_or_register("DeadPixel27", "deadpixel27@example.com")

    assert is_new is False
    assert second.user_id == first.user_id


def test_sign_in_requires_email(repo):
    provider = EmailAuthProvider(repo)
    with pytest.raises(ValueError, match="Email is required"):
        provider.sign_in_or_register("DeadPixel27", "")
