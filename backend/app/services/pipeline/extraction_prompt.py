"""Extraction prompt — template base + per-run user refinements."""

from dataclasses import replace
from typing import Optional

from app.models.domain.pipeline import PlannedStep

_FIELD_EXTRACTOR = "transform.field_extractor"


def read_prompt_from_steps(steps: list[PlannedStep]) -> str:
    """Read the field_extractor instructions from a pipeline plan."""
    for step in steps:
        if step.agent_type == _FIELD_EXTRACTOR:
            return str(step.config.get("instructions") or "").strip()
    return ""


def sync_prompt_to_steps(steps: list[PlannedStep], prompt: str) -> list[PlannedStep]:
    """Write extraction_prompt into the field_extractor step config."""
    normalized = prompt.strip()
    updated: list[PlannedStep] = []
    for step in steps:
        if step.agent_type != _FIELD_EXTRACTOR:
            updated.append(step)
            continue
        config = dict(step.config)
        config["instructions"] = normalized
        updated.append(replace(step, config=config))
    return updated


def resolve_run_extraction_prompt(
    extraction_prompt: Optional[str],
    planned_steps: list[PlannedStep],
) -> str:
    """Prefer stored run prompt; fall back to step config for legacy runs."""
    if extraction_prompt and extraction_prompt.strip():
        return extraction_prompt.strip()
    return read_prompt_from_steps(planned_steps)


def merge_prompt_addition(base_prompt: str, addition: str) -> str:
    """
    Append a generic refinement rule to the cumulative extraction prompt.

    Only reusable rules are stored — never raw chat text or document-specific values.
    """
    base = base_prompt.strip()
    extra = addition.strip()
    if not extra:
        return base
    if extra in base:
        return base
    if not base:
        return extra
    return f"{base}\n\n{extra}"
