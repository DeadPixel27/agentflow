"""Upload manifest — maps document_id → original filename."""

from __future__ import annotations

import json
from typing import Any

MANIFEST_FILENAME = "manifest.json"


def empty_manifest() -> dict[str, Any]:
    return {"documents": []}


def parse_manifest(raw: bytes | str | None) -> dict[str, Any]:
    if not raw:
        return empty_manifest()
    try:
        data = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return empty_manifest()
    if not isinstance(data, dict):
        return empty_manifest()
    docs = data.get("documents")
    if not isinstance(docs, list):
        return empty_manifest()
    return {"documents": docs}


def manifest_to_bytes(manifest: dict[str, Any]) -> bytes:
    return json.dumps(manifest, indent=2).encode("utf-8")


def upsert_manifest_entry(
    manifest: dict[str, Any],
    document_id: str,
    original_filename: str,
) -> dict[str, Any]:
    docs = list(manifest.get("documents") or [])
    updated = False
    for i, entry in enumerate(docs):
        if isinstance(entry, dict) and entry.get("document_id") == document_id:
            docs[i] = {
                **entry,
                "document_id": document_id,
                "original_filename": original_filename,
            }
            updated = True
            break
    if not updated:
        docs.append(
            {
                "document_id": document_id,
                "original_filename": original_filename,
            }
        )
    return {"documents": docs}


def original_filenames_map(manifest: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for entry in manifest.get("documents") or []:
        if not isinstance(entry, dict):
            continue
        doc_id = entry.get("document_id")
        name = entry.get("original_filename")
        if isinstance(doc_id, str) and isinstance(name, str) and name:
            result[doc_id] = name
    return result


def is_manifest_filename(name: str) -> bool:
    return name == MANIFEST_FILENAME
