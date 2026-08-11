"""Reject in-memory persistence when running as production."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_health_ok_with_memory_in_development(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)

    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")


def test_health_503_when_production_and_memory(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.setattr(
        "app.api.routes.health.get_data_backend_name",
        lambda: "memory",
    )

    response = client.get("/api/health")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unhealthy"
    assert body["persistence"] == "memory"
    assert "not allowed in production" in (body.get("detail") or "").lower()


def test_is_production_from_app_env(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    assert settings.is_production is True

    monkeypatch.setattr(settings, "app_env", "development")
    assert settings.is_production is False


def test_is_production_from_railway_env(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    assert settings.is_production is True


def test_require_persistent_backend_raises_in_production(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)

    import pytest

    with pytest.raises(RuntimeError, match="not allowed in production"):
        settings.require_persistent_backend("memory")

    # supabase is fine
    settings.require_persistent_backend("supabase")
