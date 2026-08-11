"""Document capability tokens — scoped doc_token replaces session JWT in query."""

import io
from datetime import timedelta

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from app.api.dependencies import get_doc_store, get_repo
from app.config import settings
from app.main import app
from app.models.domain.upload import UploadRecord
from app.models.domain.user import UserRecord
from app.persistence.documents.local_repository import LocalDocumentRepository
from app.persistence.memory_repository import MemoryRepository
from app.services.auth.jwt import (
    InvalidTokenError,
    create_access_token,
    create_document_access_token,
    decode_access_token,
    decode_document_access_token,
)

client = TestClient(app)


@pytest.fixture
def auth_env(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", tmp_path)
    if not settings.jwt_secret_key:
        monkeypatch.setattr(settings, "jwt_secret_key", "test-secret-for-doc-tokens")

    repo = MemoryRepository()
    user = UserRecord(user_id="user-1", name="Test", email="test@example.com")
    repo.save_user(user)
    repo.save_upload(UploadRecord(upload_id="up-1", user_id=user.user_id))
    store = LocalDocumentRepository()

    app.dependency_overrides[get_repo] = lambda: repo
    app.dependency_overrides[get_doc_store] = lambda: store
    yield {"repo": repo, "store": store, "user": user}
    app.dependency_overrides.clear()


async def _save_pdf(store: LocalDocumentRepository, upload_id: str = "up-1"):
    return await store.save_document(
        upload_id,
        UploadFile(filename="inv.pdf", file=io.BytesIO(b"%PDF-1.4 hello")),
    )


def test_document_token_roundtrip():
    token, expires = create_document_access_token("user-1", "up-1", "doc-1")
    assert expires
    claims = decode_document_access_token(
        token, upload_id="up-1", document_id="doc-1"
    )
    assert claims["user_id"] == "user-1"


def test_document_token_rejects_wrong_document():
    token, _ = create_document_access_token("user-1", "up-1", "doc-1")
    with pytest.raises(InvalidTokenError):
        decode_document_access_token(token, upload_id="up-1", document_id="other")


def test_session_token_rejected_as_document_token():
    session = create_access_token("user-1", "test@example.com")
    with pytest.raises(InvalidTokenError):
        decode_document_access_token(session, upload_id="up-1", document_id="doc-1")


def test_document_token_rejected_as_session_token():
    token, _ = create_document_access_token("user-1", "up-1", "doc-1")
    with pytest.raises(InvalidTokenError):
        decode_access_token(token)


@pytest.mark.asyncio
async def test_mint_requires_bearer(auth_env):
    store = auth_env["store"]
    saved = await _save_pdf(store)

    response = client.post(
        f"/api/uploads/up-1/documents/{saved.document_id}/access",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_mint_and_fetch_with_doc_token(auth_env):
    user = auth_env["user"]
    store = auth_env["store"]
    saved = await _save_pdf(store)
    session = create_access_token(user.user_id, user.email)

    mint = client.post(
        f"/api/uploads/up-1/documents/{saved.document_id}/access",
        headers={"Authorization": f"Bearer {session}"},
    )
    assert mint.status_code == 200, mint.text
    body = mint.json()
    assert "doc_token=" in body["url"]
    assert "access_token=" not in body["url"]
    assert body["expires_at"]

    fetch = client.get(body["url"])
    assert fetch.status_code == 200
    assert fetch.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_document_get_rejects_session_jwt_in_query(auth_env):
    user = auth_env["user"]
    store = auth_env["store"]
    saved = await _save_pdf(store)
    session = create_access_token(user.user_id, user.email)

    response = client.get(
        f"/api/uploads/up-1/documents/{saved.document_id}?access_token={session}",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_document_get_rejects_mismatched_doc_token(auth_env):
    user = auth_env["user"]
    store = auth_env["store"]
    saved = await _save_pdf(store)
    token, _ = create_document_access_token(
        user.user_id, "up-1", "wrong-doc-id"
    )

    response = client.get(
        f"/api/uploads/up-1/documents/{saved.document_id}?doc_token={token}",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_document_get_rejects_expired_doc_token(auth_env, monkeypatch):
    user = auth_env["user"]
    store = auth_env["store"]
    saved = await _save_pdf(store)
    token, _ = create_document_access_token(
        user.user_id,
        "up-1",
        saved.document_id,
        expires_delta=timedelta(seconds=-1),
    )

    response = client.get(
        f"/api/uploads/up-1/documents/{saved.document_id}?doc_token={token}",
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_document_get_accepts_bearer(auth_env):
    user = auth_env["user"]
    store = auth_env["store"]
    saved = await _save_pdf(store)
    session = create_access_token(user.user_id, user.email)

    response = client.get(
        f"/api/uploads/up-1/documents/{saved.document_id}",
        headers={"Authorization": f"Bearer {session}"},
    )
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
