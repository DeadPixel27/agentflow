"""Owner master template refining — aggregate user versions and synthesize master updates."""

import json
from typing import Any, Optional

from app.config import settings
from app.models.domain.template import PipelineTemplate
from app.persistence.protocols import DataRepository, TemplateRepository, UserTemplateStorageRepository
from app.services.llm.router import LLMTask, complete_json
from app.services.templates.user_template_version_service import UserTemplateVersionService

OWNER_SYNTHESIS_PROMPT = """\
You are a template curator. Given a master pipeline template and aggregated user
refinement feedback, propose improvements to the master template's extraction
instructions, fields, and rules.

Return ONLY valid JSON:
{
  "summary": "One sentence on what to change and why",
  "extraction_instructions": "Updated full extraction instructions",
  "fields": ["field1", "field2"],
  "rules": ["rule1", "rule2"]
}

Rules:
- Generalize patterns from user feedback — do not copy PII or document-specific values.
- Keep changes minimal and high-confidence.
- Preserve fields/rules the users did not ask to change.
"""


class TemplateMasterRefineService:
    def __init__(
        self,
        repo: DataRepository,
        templates: TemplateRepository,
        store: UserTemplateStorageRepository,
    ) -> None:
        self._repo = repo
        self._templates = templates
        self._versions = UserTemplateVersionService(repo, store)

    def list_feedback(self, template_id: Optional[str] = None, limit: int = 100) -> list[dict]:
        events = self._repo.list_refinement_events(template_id=template_id, limit=limit)
        return [
            {
                "event_id": event.event_id,
                "template_id": event.template_id,
                "version_id": event.version_id,
                "user_message": event.user_message,
                "refine_summary": event.refine_summary,
                "created_at": event.created_at,
            }
            for event in events
        ]

    async def synthesize(self, template_id: str, sample_limit: int = 20) -> dict[str, Any]:
        template = self._templates.get_template(template_id)
        if template is None:
            raise ValueError(f"Template not found: {template_id}")

        events = self._repo.list_refinement_events(template_id=template_id, limit=sample_limit)
        version_samples: list[dict[str, Any]] = []
        for event in events[:sample_limit]:
            try:
                payload = self._versions.get_version_payload(event.version_id)
                version_samples.append(
                    {
                        "refine_summary": event.refine_summary,
                        "user_message": event.user_message,
                        "extraction_prompt": payload.extraction_prompt[:2000],
                    }
                )
            except Exception:
                continue

        user_prompt = json.dumps(
            {
                "master_template": {
                    "template_id": template.template_id,
                    "extraction_instructions": template.extraction_instructions,
                    "fields": template.fields,
                    "rules": template.rules,
                },
                "user_refinement_samples": version_samples,
            },
            indent=2,
        )
        return await complete_json(
            OWNER_SYNTHESIS_PROMPT,
            user_prompt,
            task=LLMTask.REFINER,
            model=settings.groq_owner_model,
        )

    def preview_apply(self, template_id: str, synthesis: dict[str, Any]) -> PipelineTemplate:
        template = self._templates.get_template(template_id)
        if template is None:
            raise ValueError(f"Template not found: {template_id}")
        return PipelineTemplate(
            template_id=template.template_id,
            name=template.name,
            description=template.description,
            icon=template.icon,
            category=template.category,
            task_description=template.default_task,
            fields=list(synthesis.get("fields") or template.fields),
            extraction_instructions=str(
                synthesis.get("extraction_instructions") or template.extraction_instructions
            ),
            rules=list(synthesis.get("rules") or template.rules),
            output_format=template.output_format,
            suggested_steps=template.suggested_steps,
            sort_order=template.sort_order,
            is_active=template.is_active,
        )

    def apply_synthesis(self, template_id: str, synthesis: dict[str, Any]) -> PipelineTemplate:
        updated = self.preview_apply(template_id, synthesis)
        return self._templates.save_template(updated)
