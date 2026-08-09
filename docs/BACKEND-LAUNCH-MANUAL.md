# Backend Launch — Manual Checklist

Code for Phases 1–4 **and launch hardening** is in the repo. This is what **you** still need to do outside Cursor before shipping.

---

## 1. Environment variables (production + local)

In `backend/.env` (and Railway / host secrets), set:

| Variable | Required | Notes |
|----------|----------|-------|
| `OPENAI_API_KEY` | **Yes** | Extraction fails without it |
| `JWT_SECRET_KEY` | **Yes** | Generate: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `GROQ_API_KEY` | **Yes** | Planner / refine / plan-mode |
| `SUPABASE_URL` | Yes (prod) | Persistence |
| `SUPABASE_SECRET_KEY` | Yes (prod) | Persistence |
| `INBOUND_WEBHOOK_SECRET` | **Yes if inbound email enabled** | Empty secret now **rejects** all webhooks (fail closed) |
| `OCR_ENGINE` | Optional | Default `rapidocr` |
| `USE_LAYOUT_PRESERVATION` | Optional | Default `true` (Docling) |
| `FREE_PAGE_LIMIT_MONTHLY` | Optional | Default `50` |
| `GLOBAL_DAILY_PAGE_LIMIT` | Optional | Default `500` |
| `MAX_REFINES_PER_RUN` | Optional | Default `10` |
| `CORS_ORIGINS` | Prod | Comma-separated frontend URLs |

Copy from `backend/.env.example` if starting fresh.

---

## 2. Database (required)

Apply **both** migrations in the Supabase SQL editor (in order), if not already applied:

1. `backend/supabase/migrations/010_launch_tables.sql`  
   — `usage_events`, `waitlist`, `analytics_events`, `users.is_admin`
2. `backend/supabase/migrations/011_run_user_id.sql`  
   — `workflow_runs.user_id` + backfill from usage_events / workflows

Verify:

```sql
select to_regclass('public.usage_events');
select to_regclass('public.waitlist');
select to_regclass('public.analytics_events');
select column_name from information_schema.columns
  where table_name = 'users' and column_name = 'is_admin';
select column_name from information_schema.columns
  where table_name = 'workflow_runs' and column_name = 'user_id';
```

All should exist. Fresh environments can also run `backend/supabase/schema.sql` (includes `user_id` on runs).

---

## 3. Local Python

Backend venv must be **Python 3.11+** (Docling does not support 3.9).

```bash
cd backend
python3.11 -m venv .venv   # if recreating
source .venv/bin/activate
pip install -r requirements.txt
```

`backend/.python-version` is pinned to `3.11`.

---

## 4. System / deploy notes

| Item | Action |
|------|--------|
| **Tesseract** | Optional fallback if RapidOCR fails. macOS: `brew install tesseract` |
| **Docling first run** | Downloads HF models (~few minutes). Warm once before traffic. |
| **RapidOCR first run** | Downloads ONNX models on first OCR. |
| **Dockerfile** | Already `python:3.11-slim`. Rebuild/redeploy after requirements change. |
| **Railway / host** | Set all env vars above; redeploy backend from current branch. |

---

## 5. Frontend companion (not backend code)

JWT is required on protected routes. Confirm frontend:

1. Stores `token` from `POST /api/auth/session`
2. Sends `Authorization: Bearer <token>` on API calls
3. Handles `401` → re-auth
4. Handles `403` → “no access” (ownership checks are now enforced)
5. Handles `429` (monthly cap) and `503` (global cap) with user-facing copy
6. Can show run `result.field_confidence` and `result.validation_warnings`
7. Uses `GET /api/users/me` (or `/me/usage`) instead of listing all users — `GET /api/users` no longer returns everyone
8. Creates inbound addresses without a body `user_id` — server uses the JWT user (`POST /api/inbound-addresses` with `{ "workflow_id": "..." }` only)

---

## 6. Smoke test before launch

```bash
cd backend && source .venv/bin/activate
pytest tests/test_phase1_auth_llm.py tests/test_phase2_metering.py \
  tests/test_phase3_extraction.py tests/test_phase3_ship_gaps.py \
  tests/test_phase4_refine.py tests/test_hardening_gaps.py -q
```

Manual API checks:

1. `POST /api/auth/session` → get `token`
2. `GET /api/users/me/usage` with Bearer → `{ pages_used, pages_limit, resets_at }`
3. Upload + `POST /api/runs/adhoc` → run completes; poll `GET /api/runs/{id}` → `result.field_confidence` present
4. With a second user’s token, `GET /api/runs/{id}` from step 3 → **403**
5. `POST /api/workflows/{id}/runs` near monthly limit → `429`
6. `POST /api/waitlist` (no auth) → `201`
7. Failed run → usage refunded (pages drop after failure; check `/me/usage`)

---

## 7. Done by code (no manual action)

- OpenAI client + router + GPT-4o extraction with **json_schema** output mode
- JWT auth + **resource ownership** on runs / workflows / users / inbound-addresses
- Usage metering on adhoc / template / steps / workflow runs / extract / **inbound email**
- Failed runs **refund** charged pages
- Per-document field confidence + validation warnings
- Refine preview targeting + single-field re-extraction
- RapidOCR + Docling layout path
- Inbound webhook **fail-closed** when `INBOUND_WEBHOOK_SECRET` is unset

---

## 8. Out of scope / follow-ups (optional)

- Wire `users.is_admin` to admin-only routes (column exists; app does not enforce it yet)
- Upload-level ownership metadata (uploads are still keyed only by `upload_id` knowledge)
- Calibrated confidence (scores are heuristic logprob averages — do not present as exact accuracy)
