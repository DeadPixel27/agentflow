"""Domain → API mapping for user template versions."""

from app.models.api.pipeline import PlannedStepResponse
from app.models.api.template_versions import TemplateVersionDetailResponse
from app.models.domain.pipeline import PlannedStep
from app.models.domain.user_template_version import UserTemplateVersionPayload


def to_planned_step_responses(steps: list[PlannedStep]) -> list[PlannedStepResponse]:
    return [
        PlannedStepResponse(
            step_order=step.step_order,
            agent_type=step.agent_type,
            config=step.config,
            reason=step.reason,
        )
        for step in steps
    ]


def to_template_version_detail(
    payload: UserTemplateVersionPayload,
    *,
    version_number: int,
    is_current: bool,
    steps: list[PlannedStep],
) -> TemplateVersionDetailResponse:
    return TemplateVersionDetailResponse(
        version_id=payload.version_id,
        version_number=version_number,
        refine_summary=payload.refine_summary,
        parent_version_id=payload.parent_version_id,
        is_current=is_current,
        created_at=payload.created_at,
        template_id=payload.template_id,
        extraction_prompt=payload.extraction_prompt,
        user_message=payload.user_message,
        planned_steps=to_planned_step_responses(steps),
    )
