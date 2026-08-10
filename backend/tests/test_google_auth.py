"""Google auth + email-auth gate tests."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.dependencies import get_repo
from app.config import settings
from app.main import app
from app.persistence.memory_repository import MemoryRepository
from app.services.auth.google_tokens import InvalidGoogleTokenError
from app.services.auth.jwt import decode_access_token

client = TestClient(app)


def _enable_email_auth(monkeypatch):
    monkeypatch.setattr(settings, "auth_allow_email", True)


def _disable_email_auth(monkeypatch):
    monkeypatch.setattr(settings, "auth_allow_email", False)


def test_email_session_forbidden_when_disabled(monkeypatch):
    _disable_email_auth(monkeypatch)
    repo = MemoryRepository()
    app.dependency_overrides[get_repo] = lambda: repo
    try:
        response = client.post(
            "/api/auth/session",
            json={"name": "Kabir", "email": "kabir@example.com"},
        )
        assert response.status_code == 403
        assert "Google" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_email_register_user_forbidden_when_disabled(monkeypatch):
    _disable_email_auth(monkeypatch)
    repo = MemoryRepository()
    app.dependency_overrides[get_repo] = lambda: repo
    try:
        response = client.post(
            "/api/users",
            json={"name": "Kabir", "email": "kabir@example.com"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_email_session_works_when_allowed(monkeypatch):
    _enable_email_auth(monkeypatch)
    repo = MemoryRepository()
    app.dependency_overrides[get_repo] = lambda: repo
    try:
        response = client.post(
            "/api/auth/session",
            json={"name": "Kabir", "email": "kabir@example.com"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["auth_provider"] == "email"
        assert body["token"]
        payload = decode_access_token(body["token"])
        assert payload["sub"] == body["user"]["user_id"]
    finally:
        app.dependency_overrides.clear()


def test_google_session_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "")
    repo = MemoryRepository()
    app.dependency_overrides[get_repo] = lambda: repo
    try:
        response = client.post(
            "/api/auth/google",
            json={"id_token": "fake-token"},
        )
        assert response.status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_google_session_invalid_token(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")
    repo = MemoryRepository()
    app.dependency_overrides[get_repo] = lambda: repo
    try:
        with patch(
            "app.api.routes.auth.verify_google_id_token",
            side_effect=InvalidGoogleTokenError("Invalid Google ID token"),
        ):
            response = client.post(
                "/api/auth/google",
                json={"id_token": "bad-token"},
            )
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_google_session_unverified_email_rejected(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")
    repo = MemoryRepository()
    app.dependency_overrides[get_repo] = lambda: repo
    try:
        with patch(
            "app.api.routes.auth.verify_google_id_token",
            side_effect=InvalidGoogleTokenError("Google email is not verified"),
        ):
            response = client.post(
                "/api/auth/google",
                json={"id_token": "unverified-token"},
            )
        assert response.status_code == 401
        assert "not verified" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_google_session_success(monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")
    repo = MemoryRepository()
    app.dependency_overrides[get_repo] = lambda: repo
    try:
        with patch(
            "app.api.routes.auth.verify_google_id_token",
            return_value={"email": "kabir@gmail.com", "name": "Kabir Yadav"},
        ):
            response = client.post(
                "/api/auth/google",
                json={"id_token": "valid-google-token"},
            )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["auth_provider"] == "google"
        assert body["is_new_user"] is True
        assert body["user"]["email"] == "kabir@gmail.com"
        assert body["user"]["name"] == "Kabir Yadav"
        payload = decode_access_token(body["token"])
        assert payload["sub"] == body["user"]["user_id"]
        assert payload["email"] == "kabir@gmail.com"

        # Second sign-in restores same user
        with patch(
            "app.api.routes.auth.verify_google_id_token",
            return_value={"email": "kabir@gmail.com", "name": "Kabir Yadav"},
        ):
            again = client.post(
                "/api/auth/google",
                json={"id_token": "valid-google-token"},
            )
        assert again.status_code == 200
        again_body = again.json()
        assert again_body["is_new_user"] is False
        assert again_body["user"]["user_id"] == body["user"]["user_id"]
    finally:
        app.dependency_overrides.clear()


def test_verify_google_id_token_unit(monkeypatch):
    from app.services.auth.google_tokens import verify_google_id_token

    monkeypatch.setattr(settings, "google_client_id", "test-client-id.apps.googleusercontent.com")

    with patch(
        "app.services.auth.google_tokens.id_token.verify_oauth2_token",
        return_value={
            "iss": "https://accounts.google.com",
            "email": "user@example.com",
            "email_verified": True,
            "name": "Test User",
        },
    ):
        identity = verify_google_id_token("raw-token")
    assert identity == {"email": "user@example.com", "name": "Test User"}

    with patch(
        "app.services.auth.google_tokens.id_token.verify_oauth2_token",
        return_value={
            "iss": "https://accounts.google.com",
            "email": "user@example.com",
            "email_verified": False,
            "name": "Test User",
        },
    ):
        try:
            verify_google_id_token("raw-token")
            assert False, "expected InvalidGoogleTokenError"
        except InvalidGoogleTokenError as e:
            assert "not verified" in str(e)
