"""Structured logging helpers for refine / preview debugging."""

import hashlib
import json
import logging
from typing import Any, Optional


def prompt_fingerprint(prompt: str) -> str:
    if not prompt:
        return "empty"
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]


def truncate_text(text: str, limit: int = 600) -> str:
    if len(text) <= limit:
        return text
    return f"...{text[-limit:]}"


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
        "prompt_tail": truncate_text(prompt or ""),
    }
    if extra:
        payload.update(extra)
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
        snapshot = {k: fields.get(k) for k in sorted(field_filter) if k in fields}
    else:
        snapshot = {
            k: v
            for k, v in fields.items()
            if k not in ("document_id", "flags", "filename")
        }
    logger.info(
        "[refine] %s",
        json.dumps(
            {
                "phase": phase,
                "run_id": run_id,
                "document_id": document_id,
                "fields": snapshot,
            },
            default=str,
        ),
    )


def log_preview_diff(
    logger: logging.Logger,
    *,
    run_id: str,
    document_id: str,
    field: str,
    before: Any,
    after: Any,
) -> None:
    logger.info(
        "[refine] %s",
        json.dumps(
            {
                "phase": "plan-preview-diff",
                "run_id": run_id,
                "document_id": document_id,
                "field": field,
                "before": before,
                "after": after,
            },
            default=str,
        ),
    )
