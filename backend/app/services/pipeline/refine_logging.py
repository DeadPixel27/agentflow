"""Structured logging helpers for refine / preview debugging.

Production INFO logs metadata only (lengths, fingerprints, field names).
Set LOG_PAYLOADS=true for local dumps of prompt tails and field values.
"""

import hashlib
import json
import logging
from typing import Any, Optional

from app.config import settings


def prompt_fingerprint(prompt: str) -> str:
    if not prompt:
        return "empty"
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]


def truncate_text(text: str, limit: int = 600) -> str:
    if len(text) <= limit:
        return text
    return f"...{text[-limit:]}"


def _payloads_enabled() -> bool:
    return bool(settings.log_payloads)


def log_prompt(
    logger: logging.Logger,
    phase: str,
    *,
    run_id: str,
    label: str,
    prompt: str,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    payload = {
        "phase": phase,
        "run_id": run_id,
        "label": label,
        "prompt_len": len(prompt or ""),
        "prompt_fp": prompt_fingerprint(prompt or ""),
    }
    if extra:
        payload.update({k: v for k, v in extra.items() if k != "prompt_tail"})
    if _payloads_enabled():
        payload["prompt_tail"] = truncate_text(prompt or "")
    logger.info("[refine] %s", json.dumps(payload, default=str))


def log_field_snapshot(
    logger: logging.Logger,
    phase: str,
    *,
    run_id: str,
    document_id: str,
    fields: dict[str, Any],
    field_filter: Optional[set[str]] = None,
) -> None:
    if field_filter:
        names = sorted(k for k in field_filter if k in fields)
    else:
        names = sorted(
            k for k in fields if k not in ("document_id", "flags", "filename")
        )
    body: dict[str, Any] = {
        "phase": phase,
        "run_id": run_id,
        "document_id": document_id,
        "field_names": names,
    }
    if _payloads_enabled():
        if field_filter:
            body["fields"] = {k: fields.get(k) for k in names}
        else:
            body["fields"] = {k: fields[k] for k in names}
    logger.info("[refine] %s", json.dumps(body, default=str))


def log_preview_diff(
    logger: logging.Logger,
    *,
    run_id: str,
    document_id: str,
    field: str,
    before: Any,
    after: Any,
) -> None:
    body: dict[str, Any] = {
        "phase": "plan-preview-diff",
        "run_id": run_id,
        "document_id": document_id,
        "field": field,
        "changed": before != after,
    }
    if _payloads_enabled():
        body["before"] = before
        body["after"] = after
    logger.info("[refine] %s", json.dumps(body, default=str))
