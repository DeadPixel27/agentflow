"""Manual check: the generalized prompt alone must compute years_of_experience.

Runs the saved-workflow prompt against a run's cached document, with no user
example in the text, to confirm date-relative rules work on future documents.

Usage: .venv/bin/python scripts/verify_generalized_prompt.py <run_id>
"""

import asyncio
import sys

from app.persistence import get_repository, get_user_template_store
from app.services.extraction.field_extractor import DocumentInput, extract_fields
from app.services.templates.user_template_version_service import UserTemplateVersionService

FIELD = "years_of_experience"


async def main(run_id: str) -> None:
    repo = get_repository()
    versions = UserTemplateVersionService(repo, get_user_template_store())

    run = repo.get_run(run_id)
    payload = versions.get_version_payload(run.current_template_version_id)
    prompt = payload.generalized_prompt or payload.extraction_prompt

    for banned in ("2.25", "2 year", "BNY"):
        if banned in prompt:
            print(f"WARNING: generalized prompt leaks {banned!r}")

    doc = (run.cached_documents or [])[0]
    results = await extract_fields(
        [DocumentInput(doc["document_id"], doc["text"], doc.get("filename", ""))],
        ["work_experience", FIELD],
        prompt,
    )
    fields = results[0].fields
    for role in fields.get("work_experience") or []:
        print(f"  {role.get('start_date')} -> {role.get('end_date')}  {role.get('company')}")
    print(f"\ngeneralized-only {FIELD} = {fields.get(FIELD)}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1]))
