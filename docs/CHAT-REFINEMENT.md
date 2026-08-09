# AgentFlow — Chat Refinement & Workflow System

*Template → Refine → Save Workflow. The core user journey.*

---

## Concept

Templates are starting points. Workflows are user-owned customized pipelines.

```
Template (ours, read-only)
  → User runs it
  → Sees results
  → Not perfect? Opens chat: "also extract payment_status"
  → Agent modifies the pipeline config
  → User saves as their own Workflow (owned, reusable)
```

---

## What Chat Refinement Actually Changes

The chat modifies the **pipeline config**, not the raw LLM prompt. Examples:

| User says in chat | What changes in pipeline |
|-------------------|--------------------------|
| "also extract payment_status" | Adds field to `fields[]` in field_extractor step config |
| "flag invoices over ₹1L" | Adds a rule to rules step config |
| "output as JSON not CSV" | Changes `output_format` in formatter step config |
| "ignore docs without amounts" | Adds `instructions` text to field_extractor config |
| "rename vendor to supplier" | Adds field mapping instruction |

---

## Backend — Refine Endpoint

### `POST /api/runs/{run_id}/refine`

```json
{
  "message": "also extract payment_status and flag unpaid ones"
}
```

The refine endpoint:

1. Loads the current pipeline (steps + configs) from the run
2. Loads sample results from the run
3. Sends to LLM: current pipeline + results + user message
4. LLM returns modified pipeline config
5. Re-runs the pipeline with modified config
6. Returns new `run_id` for polling

### Refine System Prompt

```python
REFINE_SYSTEM_PROMPT = """\
You are a pipeline editor. Given the current pipeline definition and the user's
change request, return a MODIFIED pipeline.

Rules:
- Only change what the user asked for. Keep everything else the same.
- Return the full pipeline (all steps), not just the changed parts.
- Use the same JSON schema as the original pipeline.
- If the user wants a new field, add it to the field_extractor step's fields list.
- If the user wants a new rule/flag, add it to the rules step's rules list.
- If the user wants a format change, update the formatter step's config.
- If a step type doesn't exist yet but is needed, add it in the correct order.
"""
```

### Refine User Prompt

```python
def _build_refine_prompt(current_steps, sample_results, user_message):
    return json.dumps({
        "current_pipeline": [
            {
                "step_order": s.step_order,
                "agent_type": s.agent_type,
                "config": s.config,
                "reason": s.reason,
            }
            for s in current_steps
        ],
        "sample_results": sample_results[:3],  # first 3 rows for context
        "user_change_request": user_message,
        "required_output_schema": {
            "steps": [
                {
                    "step_order": 1,
                    "agent_type": "must be valid agent_type",
                    "config": {},
                    "reason": "why this step exists",
                }
            ]
        },
    })
```

---

## Data Model — Templates vs Workflows

**Template** (read-only, shipped by us):

- `template_id` — e.g. `"invoice"`, `"resume"`, etc.
- `name`, `description`, `icon`, `category`
- `task_description` — optimized prompt
- `fields`, `extraction_instructions`, `rules`
- `output_format`

**Workflow** (user-owned, mutable):

- `workflow_id`
- `user_id` — owner
- `source` — `"template:invoice"` | `"adhoc"` | `"chat_refined"`
- `parent_template_id` — nullable; which template it started from
- `name` — user-chosen name
- `task_description` — may be modified by chat
- `steps[]` — may be modified by chat
- `created_at`, `updated_at`

`WorkflowRecord` already has a `source` field — extend it with `parent_template_id`.

---

## Frontend — Results Page With Chat Panel

```
Results page after running a template:

┌─────────────────────────────────────────────────┐
│  Results                        [Save as Workflow] │
│ ┌─────────────────────────────────────────────┐ │
│ │ Results table (existing)                    │ │
│ │ invoice_number │ vendor │ amount │ date    │ │
│ │ INV-001        │ Acme   │ 52400  │ 2026-08 │ │
│ └─────────────────────────────────────────────┘ │
│                                                 │
│ [ ] Pipeline Steps (existing, collapsible)      │
│                                                 │
│ 💬 Refine Results                               │
│ ┌─────────────────────────────────────────────┐ │
│ │ "Not quite right? Tell me what to change."   │ │
│ │                                             │ │
│ │ User: also extract payment_status           │ │
│ │ Agent: ✓ Added payment_status field.        │ │
│ │        Re-running pipeline...               │ │
│ │                                             │ │
│ │ [Type a message...]                [Send]   │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

---

## User Flow — All Paths Lead to Saved Workflow

| User type | Path |
|-----------|------|
| **New, no idea** | Template → Run → Happy? Save as workflow |
| **New, almost happy** | Template → Run → Chat refine → Save as workflow |
| **Knows what they want** | Custom task (adhoc) → Run → Save as workflow |
| **Returning** | Open saved workflow → Upload new docs → Run |

---

## Export / Import — User Controls (Not Hardcoded)

Templates set defaults; user overrides on results page:

| Setting | UI element | Options |
|---------|------------|---------|
| **Output format** | Dropdown on results page | CSV, JSON, Excel (future) |
| **Import source** | Upload zone | File upload, Google Drive (future), URL (future) |
| **Delivery** | Button group on results page | Download, Email (future), Google Sheets (future) |

---

## Technical considerations

- **Cache OCR/text** on run record to avoid re-OCR on refine
- **Version runs** — `parent_run_id` column for lineage
- **Rate limit** refine endpoint same as ad-hoc

---

## Follow-up — derived numeric fields are computed by the LLM

Refine Apply now matches Preview, and the extractor is given `today` so
relative dates ("Present", "Current") resolve correctly. What remains is that
multi-step arithmetic is still done by the model.

Measured on a two-role resume with the generalized prompt alone:

| | `years_of_experience` |
|---|---|
| Before `today` was injected | 0.42 |
| After `today` was injected | 2.11 |
| Correct (sum of both roles) | ~2.44 |

The model resolves each date correctly but silently drops a role when summing,
so the answer is plausible and wrong — the worst failure mode for a user who
came to the chat to fix exactly this number.

**Fix:** compute derived numeric fields in Python from already-extracted
structured data. `work_experience` comes back with correct `start_date` /
`end_date` per role, so `years_of_experience` needs no LLM at all. Same pattern
applies to any total, count, or duration field.

Reproduce with `backend/scripts/verify_generalized_prompt.py <run_id>`.

**Effort:** 4–6 hours (API + chat UI + cached text storage)  
**Version:** V1.3 — after template library and deploy

---

*See [FEATURE-ROADMAP.md](./FEATURE-ROADMAP.md) Feature 4. Canonical doc — edit here, not the screenshot folders.*
