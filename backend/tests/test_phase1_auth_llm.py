"""Phase 1 smoke tests — JWT auth, protected routes, LLM router wiring."""

from fastapi.testclient import TestClient

from app.api.dependencies import get_repo
from app.main import app
from app.models.domain.user import UserRecord
from app.persistence.memory_repository import MemoryRepository
from app.services.auth.jwt import InvalidTokenError, create_access_token, decode_access_token
from app.services.llm.router import LLMTask
from tests.auth_helpers import override_current_user

client = TestClient(app)


def test_create_and_decode_access_token():
    token = create_access_token("user-abc", "user@example.com")
    payload = decode_access_token(token)
    assert payload["sub"] == "user-abc"
    assert payload["email"] == "user@example.com"


def test_decode_invalid_token_raises():
    try:
        decode_access_token("not-a-valid-token")
        assert False, "expected InvalidTokenError"
    except InvalidTokenError:
        pass


def test_session_returns_jwt_token():
    repo = MemoryRepository()
    app.dependency_overrides[get_repo] = lambda: repo
    try:
        response = client.post(
            "/api/auth/session",
            json={"name": "Kabir", "email": "kabir@example.com"},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert "token" in body
        assert body["user"]["email"] == "kabir@example.com"
        payload = decode_access_token(body["token"])
        assert payload["sub"] == body["user"]["user_id"]
        assert payload["email"] == "kabir@example.com"
    finally:
        app.dependency_overrides.clear()


def test_health_is_public():
    response = client.get("/api/health")
    assert response.status_code == 200


def test_protected_route_requires_auth():
    response = client.get("/api/templates")
    assert response.status_code == 401


def test_protected_route_accepts_bearer_token():
    repo = MemoryRepository()
    user = UserRecord(user_id="user-1", name="Test", email="test@example.com")
    repo.save_user(user)
    app.dependency_overrides[get_repo] = lambda: repo
    try:
        token = create_access_token(user.user_id, user.email)
        response = client.get(
            "/api/templates",
            headers={"Authorization": f"Bearer {token}"},
        )
        # 200 if templates seeded, or still auth-ok (not 401)
        assert response.status_code != 401
        assert response.status_code in (200, 500)
    finally:
        app.dependency_overrides.clear()


def test_protected_route_accepts_query_access_token():
    repo = MemoryRepository()
    user = UserRecord(user_id="user-1", name="Test", email="test@example.com")
    repo.save_user(user)
    app.dependency_overrides[get_repo] = lambda: repo
    try:
        token = create_access_token(user.user_id, user.email)
        response = client.get(f"/api/templates?access_token={token}")
        assert response.status_code != 401
    finally:
        app.dependency_overrides.clear()


def test_invalid_bearer_token_returns_401():
    response = client.get(
        "/api/templates",
        headers={"Authorization": "Bearer totally-bogus"},
    )
    assert response.status_code == 401


def test_router_task_enum_values():
    assert LLMTask.EXTRACTION.value == "extraction"
    assert LLMTask.PLANNER.value == "planner"
    assert LLMTask.REFINER.value == "refiner"
    assert LLMTask.PLAN_MODE.value == "plan_mode"


def test_field_extractor_imports_router():
    import inspect

    from app.services.extraction import field_extractor

    source = inspect.getsource(field_extractor)
    assert "from app.services.llm.router import" in source
    assert "LLMTask.EXTRACTION" in source
    assert "from app.services.llm.groq_client import complete_json" not in source


def test_override_current_user_helper_works():
    override_current_user()
    try:
        response = client.get("/api/templates")
        assert response.status_code != 401
    finally:
        app.dependency_overrides.clear()
