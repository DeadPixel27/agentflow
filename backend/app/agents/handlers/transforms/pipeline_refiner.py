"""Pipeline refiner agent — edits pipeline config from chat feedback."""

from typing import Any

from app.agents.core.base import StepHandler, StepResult
from app.agents.core.context import WorkflowContext
from app.agents.core.registry import register_agent
from app.persistence.serialization import planned_steps_to_json
from app.services.pipeline.extraction_prompt import sync_prompt_to_steps
from app.services.pipeline.pipeline_refiner import RefinerError, refine_pipeline

_AGENT_TYPE = "transform.pipeline_refiner"


class PipelineRefinerHandler(StepHandler):
    """
    Meta-step agent — invoked at refine time, not during normal pipeline execution.

    Expects ctx.data:
      - current_steps: list[PlannedStep]
      - sample_results: list[dict] (optional)
      - extraction_prompt: current user-layer prompt
    Expects ctx.task_description: user's refinement message.
    """

    async def execute(
        self,
        ctx: WorkflowContext,
        config: dict[str, Any],
    ) -> StepResult:
        current_steps = ctx.data.get("current_steps")
        if not current_steps:
            raise ValueError(f"{_AGENT_TYPE} requires current_steps in context")

        sample_results = ctx.data.get("sample_results", [])
        message = ctx.task_description or config.get("message", "")
        if not message.strip():
            raise ValueError(f"{_AGENT_TYPE} requires a refinement message")

        base_prompt = str(ctx.data.get("extraction_prompt") or "")
        previous_refinements = ctx.data.get("previous_refinements", [])
        try:
            steps, summary, extraction_prompt = await refine_pipeline(
                current_steps,
                sample_results,
                message,
                base_prompt=base_prompt,
                previous_refinements=previous_refinements,
            )
        except RefinerError as exc:
            raise ValueError(str(exc)) from exc

        steps = sync_prompt_to_steps(steps, extraction_prompt)

        return StepResult(
            output={
                "summary": summary,
                "extraction_prompt": extraction_prompt,
                "planned_steps": planned_steps_to_json(steps),
            }
        )


register_agent(
    _AGENT_TYPE,
    name="Pipeline Refiner",
    description=(
        "Edit an existing pipeline from chat feedback — add fields, rules, "
        "or update the full extraction prompt. Invoked on refine, not as a run step."
    ),
    example_config={
        "message": "also extract payment_status and flag unpaid invoices",
    },
    handler=PipelineRefinerHandler(),
)
