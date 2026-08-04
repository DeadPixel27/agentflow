# Manual API Test Guide

Interactive walkthrough for the main user flow. **Do one step at a time**, paste the response in chat, and you'll get the exact payload for the next step.

---

## Before you start

**1. Start the server**

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```

Base URL: `http://localhost:8000`  
Swagger UI: `http://localhost:8000/docs`

**2. Sample file**

Use any PDF — `backend/samples/test_invoice.pdf` or your own resume/invoice.

**3. Track these values** (fill in as you go)

| Variable       | Value |
|----------------|-------|
| `user_id`      |       |
| `upload_id`    |       |
| `document_id`  |       |
| `run_id`       |       |
| `workflow_id`  |       |
| `upload_id_2`  |       |

---

## Step 0 (optional) — Health check

**Request**

```bash
curl http://localhost:8000/api/health
```

**Expected:** `{"status":"ok"}` (or similar)

Paste the response in chat if anything looks wrong, then continue to Step 1.

---

## Step 1 — Create user

**What it does:** Creates a user who will own workflows. No auth yet — the `user_id` scopes workflows to this user.

### curl

```bash
curl -X POST http://localhost:8000/api/users \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kabir",
    "email": "kabir@example.com"
  }'
```

### Swagger

`POST /api/users` → body above → Execute

### What to look for

- HTTP `200`
- `user_id` in the response (UUID) — save this for Step 4

### Example response

```json
{
  "user_id": "78f821dc-f526-4167-ab23-032f4ea617c2",
  "name": "Kabir",
  "email": "kabir@example.com",
  "created_at": null
}
```

### Your turn

1. Create a user.
2. Paste the full JSON response in chat.

**Next step:** upload a document.

---

## Step 2 — Upload documents

**What it does:** Uploads file(s), extracts text, returns `upload_id` and per-file `document_id`.

### curl

```bash
curl -X POST http://localhost:8000/api/upload \
  -F "files=@samples/test_invoice.pdf"
```

### Swagger

`POST /api/upload` → choose a PDF → Execute

### What to look for

- HTTP `200`
- `upload_id` — batch ID for later API calls
- `documents[].document_id` — one per file (saved on the run in Step 3)

### Your turn

Paste the full JSON response in chat.

**Next step:** adhoc run using your `upload_id`.

---

## Step 3 — Adhoc run (plan + execute)

_Status: waiting for Step 2 response_

You'll run:

```
POST /api/runs/adhoc
```

Payload will be provided in chat using your `upload_id`.

### What to look for in the response

- `run_id` — save for Step 4
- `document_ids` — list of doc IDs used in this run
- `planned_steps` — the plan that was executed
- `workflow_id` — `null` until you save the workflow
- `result` — extracted output

---

## Step 4 — Save workflow from run

_Status: waiting for Step 3 response_

You'll run:

```
POST /api/workflows/from-run/{run_id}
```

Requires `user_id` from Step 1. No re-planning — saves `planned_steps` from your adhoc run.

### What to look for

- `workflow_id` — save for Steps 6–7
- `user_id` — matches your user from Step 1
- The original adhoc run gets `workflow_id` backfilled when you save

---

## Step 5 — Upload again (new batch)

_Status: waiting for Step 4 response_

Same as Step 2 — upload a new file to test workflow reuse.

You'll get a new `upload_id` (and new `document_id`).

---

## Step 6 — Run saved workflow

_Status: waiting for Step 5 response_

You'll run:

```
POST /api/workflows/{workflow_id}/runs
```

Planner is skipped. Saved steps run on the new upload.

### What to look for

- `workflow_id` — set to your saved workflow
- `document_ids` — doc IDs from the new upload batch

---

## Step 7 (optional) — View run history

After Step 6, try these:

**All runs for a workflow**

```bash
curl http://localhost:8000/api/workflows/{workflow_id}/runs
```

**All workflows for a user**

```bash
curl http://localhost:8000/api/users/{user_id}/workflows
```

**Filter workflows by user**

```bash
curl "http://localhost:8000/api/workflows?user_id={user_id}"
```

---

## Full flow (reference)

```
POST /api/users                          → user_id
POST /api/upload                         → upload_id, document_id
POST /api/runs/adhoc                     → run_id, document_ids, planned_steps
POST /api/workflows/from-run/{run_id}    → workflow_id (needs user_id)
POST /api/upload                         → upload_id_2
POST /api/workflows/{workflow_id}/runs   → rerun without planner
GET  /api/workflows/{workflow_id}/runs   → all runs for this workflow
```

---

## Data model

```
User
  └── Workflow (user_id)
        └── Run (workflow_id)
              ├── upload_id
              └── document_ids[]
```

---

## Troubleshooting

| Issue | Check |
|-------|--------|
| `Connection refused` | Server running? `uvicorn app.main:app --reload` |
| `404 User not found` | Create user first (Step 1); use correct `user_id` when saving workflow |
| `404 Upload not found` | Use `upload_id` from the most recent upload on this server instance |
| `502` on adhoc/run | `GROQ_API_KEY` set in `backend/.env` |
| Empty `extracted_text` | Try a different PDF or check file isn't corrupted |
| Data lost after restart | Without Supabase, users/workflows/runs are in-memory only |
| Supabase migration needed | Run `supabase/migrations/002_add_users_and_run_document_ids.sql` |

---

## Start here

Run **Step 1** (create user) and paste the response in chat.
