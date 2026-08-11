"""Health endpoint tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("ok", "degraded")
    assert data["service"] == "nexora-api"
    assert data["persistence"] in ("memory", "supabase")
    assert "database" in data
    assert data["document_storage"] in ("local", "supabase")
