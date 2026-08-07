"""Supabase Storage repository for user template version payloads."""

import json
import logging
from typing import Any

from app.config import settings
from app.persistence.supabase_repository import get_supabase_client

logger = logging.getLogger("user_template_storage")


class SupabaseUserTemplateRepository:
    backend_name = "supabase"

    def _bucket(self) -> str:
        return settings.supabase_user_templates_bucket

    def build_storage_key(self, scope_type: str, scope_id: str, version_id: str) -> str:
        return f"{scope_type}s/{scope_id}/{version_id}.json"

    def save_version(self, storage_key: str, payload: dict[str, Any]) -> str:
        body = json.dumps(payload, indent=2).encode("utf-8")
        get_supabase_client().storage.from_(self._bucket()).upload(
            storage_key,
            body,
            file_options={
                "content-type": "application/json",
                "upsert": "true",
            },
        )
        return storage_key

    def load_version(self, storage_key: str) -> dict[str, Any]:
        data = get_supabase_client().storage.from_(self._bucket()).download(storage_key)
        return json.loads(data.decode("utf-8"))

    def delete_version(self, storage_key: str) -> None:
        get_supabase_client().storage.from_(self._bucket()).remove([storage_key])
