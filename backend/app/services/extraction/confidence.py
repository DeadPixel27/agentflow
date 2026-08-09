"""
Per-field confidence scoring using OpenAI token logprobs.

HOW IT WORKS:
1. OpenAI returns log-probabilities for each output token
2. We map tokens back to the JSON field values in the extraction output
3. For each field, we compute mean(exp(logprob)) across its value tokens
4. Result: confidence score 0.0-1.0 per extracted field

Based on Azure's open-source implementation:
github.com/azure/ai-document-processing-pipeline
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any

logger = logging.getLogger("confidence")


def compute_field_confidence(
    parsed: dict[str, Any],
    logprobs: list[Any] | None,
    fields: list[str],
) -> dict[str, float]:
    """
    Compute per-field confidence scores from token logprobs.

    Returns: dict mapping field name -> confidence (0.0 to 1.0)
    Averaged across documents when multiple results are present.
    Prefer compute_document_field_confidence for multi-doc extractions.
    """
    by_doc = compute_document_field_confidence(parsed, logprobs, fields)
    if not by_doc:
        return {field: 0.5 for field in fields}

    averages: dict[str, list[float]] = {field: [] for field in fields}
    for conf in by_doc.values():
        for field in fields:
            averages[field].append(conf.get(field, 0.5))

    return {
        field: round(sum(vals) / len(vals), 4) if vals else 0.5
        for field, vals in averages.items()
    }


def compute_document_field_confidence(
    parsed: dict[str, Any],
    logprobs: list[Any] | None,
    fields: list[str],
) -> dict[str, dict[str, float]]:
    """
    Compute per-document, per-field confidence from token logprobs.

    Returns: {document_id: {field: confidence}}
    """
    results = parsed.get("results", [])
    if not results:
        return {}

    if not logprobs:
        logger.debug("No logprobs available - returning default confidence")
        return {
            str(item.get("document_id") or idx): {field: 0.5 for field in fields}
            for idx, item in enumerate(results)
            if isinstance(item, dict)
        }

    tokens_with_probs: list[tuple[str, float]] = [
        (token_info.token, token_info.logprob) for token_info in logprobs
    ]

    by_doc: dict[str, dict[str, float]] = {}
    for idx, result_item in enumerate(results):
        if not isinstance(result_item, dict):
            continue
        doc_id = str(result_item.get("document_id") or idx)
        result_fields = result_item.get("fields", {}) or {}
        field_scores: dict[str, float] = {}
        for field in fields:
            value = result_fields.get(field)
            if value is None:
                field_scores[field] = 0.5
                continue

            value_str = json.dumps(value) if not isinstance(value, str) else value
            # Prefer the Nth occurrence of the field name for the Nth document
            probs = _find_value_token_probs(
                tokens_with_probs,
                field,
                value_str,
                occurrence=idx,
            )
            if probs:
                field_scores[field] = round(sum(probs) / len(probs), 4)
            else:
                all_probs = [math.exp(lp) for _, lp in tokens_with_probs if lp != 0.0]
                field_scores[field] = (
                    round(sum(all_probs) / len(all_probs), 4) if all_probs else 0.5
                )
        by_doc[doc_id] = field_scores

    return by_doc


def _find_value_token_probs(
    tokens_with_probs: list[tuple[str, float]],
    field_name: str,
    value_str: str,
    *,
    occurrence: int = 0,
) -> list[float]:
    """
    Find tokens corresponding to a field's value in the token stream.

    Strategy: look for the Nth field name token(s), then collect the value tokens
    that follow until the next field delimiter (comma, closing brace).
    """
    del value_str  # reserved for future exact-value matching

    full_text = "".join(t for t, _ in tokens_with_probs)

    field_pattern = f'"{field_name}"'
    search_from = 0
    field_pos = -1
    for _ in range(max(occurrence, 0) + 1):
        field_pos = full_text.find(field_pattern, search_from)
        if field_pos == -1:
            break
        search_from = field_pos + len(field_pattern)

    if field_pos == -1:
        field_pattern = f'"{field_name.replace("_", " ")}"'
        field_pos = full_text.find(field_pattern)
        if field_pos == -1:
            return []

    colon_pos = full_text.find(":", field_pos + len(field_pattern))
    if colon_pos == -1:
        return []

    char_pos = 0
    value_start_token_idx: int | None = None
    for idx, (token_text, _) in enumerate(tokens_with_probs):
        if char_pos >= colon_pos and value_start_token_idx is None:
            value_start_token_idx = idx
            break
        char_pos += len(token_text)

    if value_start_token_idx is None:
        return []

    probs: list[float] = []
    depth = 0
    started = False
    for idx in range(value_start_token_idx, len(tokens_with_probs)):
        token_text, logprob = tokens_with_probs[idx]
        stripped = token_text.strip()

        if not started:
            if stripped in (":", ""):
                continue
            started = True

        for ch in stripped:
            if ch in ("{", "["):
                depth += 1
            elif ch in ("}", "]"):
                depth -= 1

        if depth < 0:
            break
        if depth == 0 and "," in stripped and not stripped.startswith('"'):
            break

        prob = math.exp(logprob) if logprob != 0.0 else 1.0
        probs.append(prob)

    return probs
