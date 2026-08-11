"""PATCH /api/users/me — update display name."""

from fastapi.testclient import TestClient

from app.api.dependencies import get_repo
from app.main import app
from app.models.domain.user import UserRecord
from app.persistence.memory_repository import MemoryRepository
from tests.auth_helpers import auth_user, override_current_user

client = TestClient(app)


def test_patch_me_updates_display_name():
    repo = MemoryRepository()
    repo.save_user(
        UserRecord(
            user_id="user-1",
            name="Old Name",
            email="user@example.com",
        )
    )
    app.dependency_overrides[get_repo] = lambda: repo
    override_current_user(auth_user(user_id="user-1", name="Old Name"))
    try:
        response = client.patch("/api/users/me", json={"name": "  New Name  "})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["name"] == "New Name"
        assert body["user_id"] == "user-1"
        assert repo.get_user("user-1").name == "New Name"
    finally:
        app.dependency_overrides.clear()


def test_patch_me_rejects_blank_name():
    repo = MemoryRepository()
    repo.save_user(
        UserRecord(
            user_id="user-1",
            name="Old Name",
            email="user@example.com",
        )
    )
    app.dependency_overrides[get_repo] = lambda: repo
    override_current_user(auth_user(user_id="user-1", name="Old Name"))
    try:
        response = client.patch("/api/users/me", json={"name": "   "})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
