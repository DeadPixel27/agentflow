"""Preview extraction with proposed refinement — before expensive full re-run."""

import logging
from typing import Any, Optional

from app.models.domain.run import RunResult
from app.services.extraction.field_extractor import DocumentInput, extract_fields
from app.services.pipeline.extraction_prompt import merge_prompt_addition
from app.services.pipeline.refine_logging import (
    log_field_snapshot,
    log_preview_diff,
    log_prompt,
    prompt_fingerprint,
)
from app.services.templates.user_template_version_service import UserTemplateVersionService

logger = logging.getLogger("refine_preview")

_SKIP_ROW_KEYS = frozenset({"document_id", "flags", "filename"})
_MAX_PREVIEW_DOCS = 2
_MAX_PREVIEW_FIELDS = 10


def _field_names_from_steps(planned_steps: list) -> list[str]:
    for step in planned_steps:
        if step.agent_type == "transform.field_extractor":
            fields = step.config.get("fields", [])
            if isinstance(fields, list):
                return [str(f) for f in fields]
    return []


def _infer_target_fields(
    accumulated_instruction: str,
    planned_changes: list[str],
    all_fields: list[str],
) -> set[str]:
    """Match field names from instruction/changes, handling underscores and spaces."""
    haystack = " ".join([accumulated_instruction, *planned_changes]).lower()
    matched: set[str] = set()

    for field in all_fields:
        field_lower = field.lower()
        # Direct match
        if field_lower in haystack:
            matched.add(field)
            continue
        # Underscore -> space match (e.g. "vendor_name" matches "vendor name")
        field_spaced = field_lower.replace("_", " ")
        if field_spaced in haystack:
            matched.add(field)
            continue

        # Space -> underscore match
        field_underscored = field_lower.replace(" ", "_")
        if field_underscored in haystack:
            matched.add(field)
            continue

        # Partial word match (e.g. "vendor" in "fix vendor")
        for word in field_lower.replace("_", " ").split():
            if len(word) >= 4 and word in haystack:
                matched.add(field)
                break

    return matched


def _format_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return value[:3] if len(value) > 3 else value
    if isinstance(value, dict):
        return value
    return str(value)


def _values_equivalent(a: Any, b: Any) -> bool:
    """Compare values with normalization to avoid false diffs."""
    if a == b:
        return True
    if a is None or b is None:
        return False
    # String normalization: strip whitespace, case-insensitive
    if isinstance(a, str) and isinstance(b, str):
        return a.strip().lower() == b.strip().lower()
    # Numeric: compare with tolerance
    try:
        fa, fb = float(a), float(b)
        return abs(fa - fb) < 0.01
    except (ValueError, TypeError):
        pass
    return str(a).strip() == str(b).strip()


async def preview_refinement(
    run: RunResult,
    versions: UserTemplateVersionService,
    accumulated_instruction: str,
    planned_changes: Optional[list[str]] = None,
) -> list[dict[str, Any]]:
    """
    Re-extract sample documents with base prompt + proposed instruction.

    Returns rows with before/after per field for UI preview when ready to Apply.

    NOTE: Preview uses merge(base_prompt, accumulated_instruction) directly.
    Apply (/refine) runs the pipeline refiner first — prompts may differ.
    """
    instruction = accumulated_instruction.strip()
    if not instruction:
        logger.info(
            "[refine] preview skipped run_id=%s reason=empty_instruction",
            run.run_id,
        )
        return []

    documents = run.cached_documents or []
    if not documents:
        logger.warning(
            "[refine] preview skipped run_id=%s reason=no_cached_documents",
            run.run_id,
        )
        return []

    planned_steps, base_prompt = versions.resolve_run_plan(run)
    preview_prompt = merge_prompt_addition(base_prompt, instruction)
    fields = _field_names_from_steps(planned_steps)

    log_prompt(
        logger,
        "plan-preview",
        run_id=run.run_id,
        label="base_prompt",
        prompt=base_prompt,
    )
    log_prompt(
        logger,
        "plan-preview",
        run_id=run.run_id,
        label="accumulated_instruction",
        prompt=instruction,
    )
    log_prompt(
        logger,
        "plan-preview",
        run_id=run.run_id,
        label="preview_prompt_merged",
        prompt=preview_prompt,
        extra={
            "note": "Preview merges instruction into base directly; Apply uses refiner output",
            "base_fp": prompt_fingerprint(base_prompt),
            "preview_fp": prompt_fingerprint(preview_prompt),
            "planned_changes": planned_changes or [],
        },
    )

    rows = (run.result or {}).get("rows", [])
    if not fields and rows:
        fields = [
            str(key)
            for key in rows[0]
            if str(key) not in _SKIP_ROW_KEYS
        ]

    if not fields:
        logger.warning(
            "[refine] preview skipped run_id=%s reason=no_fields",
            run.run_id,
        )
        return []

    target_fields = _infer_target_fields(
        instruction,
        planned_changes or [],
        fields,
    )
    logger.info(
        "[refine] preview run_id=%s target_fields=%s all_fields_count=%d doc_count=%d",
        run.run_id,
        sorted(target_fields),
        len(fields),
        min(len(documents), _MAX_PREVIEW_DOCS),
    )

    # Only show diffs for targeted fields. If no targets matched,
    # skip field-level preview entirely (show planned_changes text only).
    if not target_fields:
        logger.info(
            "[refine] preview: no target fields matched, skipping field-level diff run_id=%s",
            run.run_id,
        )
        return []

    preview_rows: list[dict[str, Any]] = []
    for doc in documents[:_MAX_PREVIEW_DOCS]:
        doc_id = str(doc.get("document_id", ""))
        text = str(doc.get("text", "")).strip()
        if not doc_id or not text:
            continue

        before_row: dict[str, Any] = {}
        for row in rows:
            if row.get("document_id") == doc_id:
                before_row = row
                break
        if not before_row and rows:
            before_row = rows[0]

        log_field_snapshot(
            logger,
            "plan-preview-before",
            run_id=run.run_id,
            document_id=doc_id,
            fields=before_row,
            field_filter=target_fields or None,
        )

        try:
            extracted = await extract_fields(
                [
                    DocumentInput(
                        document_id=doc_id,
                        filename=str(doc.get("filename", "")),
                        text=text,
                    )
                ],
                fields,
                preview_prompt,
            )
        except Exception as exc:
            logger.warning(
                "[refine] preview extraction failed run_id=%s doc_id=%s error=%s",
                run.run_id,
                doc_id,
                exc,
                exc_info=True,
            )
            continue

        after_fields = extracted[0].fields if extracted else {}
        log_field_snapshot(
            logger,
            "plan-preview-after",
            run_id=run.run_id,
            document_id=doc_id,
            fields=after_fields,
            field_filter=target_fields or None,
        )

        field_previews: list[dict[str, Any]] = []

        candidates = target_fields
        for field in fields:
            if field not in candidates:
                continue
            before = _format_value(before_row.get(field))
            after = _format_value(after_fields.get(field))
            # Normalize for comparison to avoid false diffs from LLM non-determinism
            if _values_equivalent(before, after):
                continue
            log_preview_diff(
                logger,
                run_id=run.run_id,
                document_id=doc_id,
                field=field,
                before=before,
                after=after,
            )
            field_previews.append(
                {
                    "field": field,
                    "before": before,
                    "after": after,
                }
            )
            if len(field_previews) >= _MAX_PREVIEW_FIELDS:
                break

        if not field_previews and target_fields:
            for field in sorted(target_fields):
                if field not in fields:
                    continue
                before = _format_value(before_row.get(field))
                after = _format_value(after_fields.get(field))
                log_preview_diff(
                    logger,
                    run_id=run.run_id,
                    document_id=doc_id,
                    field=field,
                    before=before,
                    after=after,
                )
                field_previews.append(
                    {
                        "field": field,
                        "before": before,
                        "after": after,
                    }
                )
                if len(field_previews) >= _MAX_PREVIEW_FIELDS:
                    break

        if field_previews:
            preview_rows.append(
                {
                    "document_id": doc_id,
                    "filename": str(doc.get("filename") or before_row.get("filename") or ""),
                    "fields": field_previews,
                }
            )

    logger.info(
        "[refine] preview complete run_id=%s preview_rows=%d",
        run.run_id,
        len(preview_rows),
    )
    return preview_rows
