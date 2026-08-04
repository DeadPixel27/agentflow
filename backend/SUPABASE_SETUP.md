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
4. You should see `Success. No rows returned`

Tables created:

| Table | Purpose |
|-------|---------|
| `users` | App users |
| `workflows` | Saved workflow templates |
| `workflow_steps` | Steps per workflow |
| `workflow_runs` | Execution history |
| `workflow_step_runs` | Per-step run output |

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

## 5. Verify

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
  "database": "connected"
}
```

## 6. Confirm persistence

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

## Optional: view data

Supabase Dashboard → **Table Editor** → browse `users`, `workflows`, `workflow_runs`.
