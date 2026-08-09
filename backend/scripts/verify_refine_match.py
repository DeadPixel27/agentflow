"""Manual check: Preview and Apply must produce the same years_of_experience.

Usage: .venv/bin/python scripts/verify_refine_match.py <parent_run_id>
"""

import asyncio
import sys

from app.persistence import get_repository, get_user_template_store
from app.services.pipeline.refine_chat import plan_refinement
from app.services.pipeline.refine_logging import prompt_fingerprint
from app.services.pipeline.refine_preview import preview_refinement
from app.services.pipeline.refine_service import RefineService
from app.services.pipeline.runner import execute_run
from app.services.templates.user_template_version_service import UserTemplateVersionService

FIELD = "years_of_experience"
USER_MESSAGES = [
    "years of exp is wrong",
    "july 24 - present(aug 26) = 2 year + another experience of 2 months gives total = 2.25",
]


async def main(parent_run_id: str) -> None:
    repo = get_repository()
    versions = UserTemplateVersionService(repo, get_user_template_store())

    parent = versions.hydrate_run(repo.get_run(parent_run_id))
    rows = (parent.result or {}).get("rows") or []
    field_names = [k for k in rows[0]] if rows else []
    print(f"parent {parent_run_id} {FIELD} before = {rows[0].get(FIELD) if rows else None}")

    chat: list[dict[str, str]] = []
    plan = {}
    for message in USER_MESSAGES:
        plan = await plan_refinement(message, chat, field_names, rows[:2])
        chat.append({"role": "user", "content": message})
        chat.append({"role": "assistant", "content": plan["message"]})
        print(f"plan ready={plan['ready']} instruction_len={len(plan['accumulated_instruction'])}")

    instruction = plan["accumulated_instruction"]
    if not instruction:
        print("no accumulated_instruction — plan never became ready")
        return
    print(f"\ninstruction:\n{instruction}\n")

    preview = await preview_refinement(parent, versions, instruction, plan["planned_changes"])
    preview_value = None
    for row in preview:
        for change in row.get("fields", []):
            if change.get("field") == FIELD:
                preview_value = change.get("after")
    print(f"PREVIEW {FIELD} = {preview_value}")

    service = RefineService(repo, versions)
    child, summary = await service.refine_and_start(parent_run_id, instruction)
    if child.status == "running":
        await execute_run(child.run_id)
        child = repo.get_run(child.run_id)

    child_rows = (child.result or {}).get("rows") or []
    apply_value = child_rows[0].get(FIELD) if child_rows else None
    print(f"APPLY   {FIELD} = {apply_value}")

    payload = versions.get_version_payload(child.current_template_version_id)
    print(f"\nversion extraction_prompt fp = {prompt_fingerprint(payload.extraction_prompt)}")
    print(f"version generalized_prompt fp = {prompt_fingerprint(payload.generalized_prompt or '')}")
    print(f"\ngeneralized (Save Workflow would use):\n{payload.generalized_prompt}")
    print(f"\nsummary: {summary}")
    print(f"\nMATCH: {preview_value == apply_value}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
