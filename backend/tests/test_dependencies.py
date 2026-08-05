"""FastAPI dependency injection tests."""

from fastapi.testclient import TestClient

from app.api.dependencies import get_repo
from app.main import app
from app.persistence.memory_repository import MemoryRepository

client = TestClient(app)


def test_health_uses_injected_memory_repository():
    """Routes can swap persistence via dependency_overrides (no real DB needed)."""
    memory = MemoryRepository()
    app.dependency_overrides[get_repo] = lambda: memory
    try:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "in_memory"
    finally:
        app.dependency_overrides.clear()
