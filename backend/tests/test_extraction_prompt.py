"""Tests for per-run extraction prompt layering."""

from app.models.domain.pipeline import PlannedStep
from app.services.pipeline.extraction_prompt import (
    effective_preview_prompt,
    merge_prompt_addition,
    read_prompt_from_steps,
    resolve_run_extraction_prompt,
    sync_prompt_to_steps,
)


def test_read_and_sync_prompt_on_field_extractor():
    steps = [
        PlannedStep(
            step_order=1,
            agent_type="transform.field_extractor",
            config={"fields": ["amount"], "instructions": "old"},
            reason="extract",
        ),
    ]
    updated = sync_prompt_to_steps(steps, "template base prompt")
    assert read_prompt_from_steps(updated) == "template base prompt"


def test_merge_prompt_addition_appends_generic_rule_only():
    base = "years_of_experience from earliest job"
    addition = (
        "When calculating years_of_experience, sum all role durations including "
        "internships. Round to one decimal. Do not use education dates."
    )
    prompt = merge_prompt_addition(base, addition)
    assert base in prompt
    assert addition in prompt
    assert "BNY" not in prompt
    assert "2.5" not in prompt


def test_merge_prompt_addition_skips_duplicate():
    base = "rule one\n\nrule two"
    assert merge_prompt_addition(base, "rule two") == base


def test_effective_preview_prompt_matches_merge():
    base = "Extract years_of_experience from work history"
    instruction = "Sum each role duration; return fractional years."
    assert effective_preview_prompt(base, instruction) == merge_prompt_addition(
        base, instruction
    )


def test_resolve_run_extraction_prompt_prefers_stored_value():
    steps = [
        PlannedStep(
            step_order=1,
            agent_type="transform.field_extractor",
            config={"fields": ["x"], "instructions": "from steps"},
            reason="extract",
        ),
    ]
    assert resolve_run_extraction_prompt("stored prompt", steps) == "stored prompt"
    assert resolve_run_extraction_prompt(None, steps) == "from steps"
