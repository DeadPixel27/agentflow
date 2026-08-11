"""Local filesystem storage for user template version payloads."""

import json
from pathlib import Path
from typing import Any

from app.config import settings


class LocalUserTemplateRepository:
    backend_name = "local"

    def _base_dir(self) -> Path:
        return settings.upload_dir / "user-templates"

    def _object_path(self, storage_key: str) -> Path:
        return self._base_dir() / storage_key

    def build_storage_key(self, scope_type: str, scope_id: str, version_id: str) -> str:
        return f"{scope_type}s/{scope_id}/{version_id}.json"

    def save_version(self, storage_key: str, payload: dict[str, Any]) -> str:
        path = self._object_path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return storage_key

    def load_version(self, storage_key: str) -> dict[str, Any]:
        path = self._object_path(storage_key)
        if not path.is_file():
            raise FileNotFoundError(f"User template version not found: {storage_key}")
        return json.loads(path.read_text(encoding="utf-8"))

    def delete_version(self, storage_key: str) -> None:
        path = self._object_path(storage_key)
        if path.is_file():
            path.unlink()
