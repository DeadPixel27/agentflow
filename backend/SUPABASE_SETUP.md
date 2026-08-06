# Supabase setup guide

Follow these steps to persist users, workflows, and runs in Postgres (survives server restarts).

## 1. Create a project

1. Go to [https://supabase.com](https://supabase.com) and sign in
2. **New project** → pick org, name (e.g. `agentflow`), database password, region
3. Wait ~2 minutes for provisioning

## 2. Run the schema

1. In Supabase Dashboard → **SQL Editor** → **New query**
2. Copy the entire contents of [`supabase/schema.sql`](supabase/schema.sql)
3. Click **Run**
4. Run [`supabase/seed_templates.sql`](supabase/seed_templates.sql) the same way (pipeline template catalog)
5. You should see `Success` for both

Tables created:

| Table | Purpose |
|-------|---------|
| `users` | App users |
| `workflows` | Saved workflow templates |
| `workflow_steps` | Steps per workflow |
| `workflow_runs` | Execution history |
| `workflow_step_runs` | Per-step run output |
| `pipeline_templates` | Landing-page task presets (editable in Table Editor) |

> **Existing project?** Run [`supabase/migrations/002_add_users_and_run_document_ids.sql`](supabase/migrations/002_add_users_and_run_document_ids.sql) instead if you already had an older schema.

## 3. Get API keys

1. Dashboard → **Project Settings** → **API**
2. Copy:
   - **Project URL** → `SUPABASE_URL`
   - **Secret key** (`sb_secret_...`) → `SUPABASE_SECRET_KEY`

Use the **secret** key on the backend only — never expose it in the frontend.

## 4. Update `.env`

```bash
cd backend
cp .env.example .env   # if you haven't already
```

Add to `backend/.env`:

```env
SUPABASE_URL=https://xxxxxxxx.supabase.co
SUPABASE_SECRET_KEY=sb_secret_xxxxxxxx
```

Keep your existing `GROQ_API_KEY` line.

## 5. Enable document storage (Supabase Storage)

Uploaded PDFs/images can be stored in Supabase instead of local disk. This is required for production deploys (Railway/Vercel).

### Create the bucket

1. Dashboard → **Storage** → **New bucket**
2. Name: `documents` (must match `SUPABASE_DOCUMENTS_BUCKET` in `.env`)
3. **Public bucket**: OFF (backend serves files via API using the secret key)
4. Click **Create bucket**

### Configure `.env`

```env
DOCUMENT_STORAGE=auto
SUPABASE_DOCUMENTS_BUCKET=documents
```

| `DOCUMENT_STORAGE` | Behavior |
|--------------------|----------|
| `auto` (default) | Supabase Storage when `SUPABASE_*` is set, else `backend/uploads/` |
| `local` | Always local disk |
| `supabase` | Always Supabase Storage |

Restart the server after changing env vars.

## 6. Verify

```bash
cd backend
source .venv/bin/activate
python scripts/verify_supabase.py
```

Expected:

```
OK: Connected to Supabase
  OK  table: users
  OK  table: workflows
  ...
All checks passed.
```

Restart the server:

```bash
uvicorn app.main:app --reload
```

Check health:

```bash
curl http://localhost:8000/api/health
```

Expected:

```json
{
  "status": "ok",
  "service": "agentflow-api",
  "persistence": "supabase",
  "database": "connected",
  "document_storage": "supabase"
}
```

## 7. Confirm persistence

1. Create a user via API
2. **Restart** uvicorn
3. `GET /api/users` — user should still exist

Without Supabase, data is in-memory and lost on restart.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `not_configured` in health | Add both env vars to `.env`, restart server |
| `relation "users" does not exist` | Run `schema.sql` in SQL Editor |
| `Invalid API key` | Use **secret** key, not publishable |
| `degraded` status | Run `python scripts/verify_supabase.py` for details |
| RLS errors | Backend uses service role key; RLS is bypassed |
| `Bucket not found` | Create `documents` bucket in Storage (step 5) |
| Files 404 after deploy | Set `DOCUMENT_STORAGE=auto` and configure Supabase Storage |

## Optional: view data

Supabase Dashboard → **Table Editor** → browse `users`, `workflows`, `workflow_runs`.
