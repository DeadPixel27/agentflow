# Nexora — Deployment & Secrets

How we run production: hosts, where env vars live, and the ship checklist.

**Status:** Deploy is planned but not live yet. See [NEXT-STEPS.md](./NEXT-STEPS.md).

---

## Topology

```
User → Vercel (Next.js frontend)
         │  HTTPS REST
         ▼
       Railway (FastAPI backend, Docker)
         │
         ├── Supabase (Postgres + private Storage)
         ├── OpenAI / Groq (LLMs)
         ├── Resend (outbound email)      [optional]
         └── Mailgun (inbound webhooks)   [optional]
```

| Layer | Host | Role |
|-------|------|------|
| Frontend | **Vercel** | Next.js App Router |
| Backend | **Railway** | FastAPI via [`backend/Dockerfile`](../backend/Dockerfile) |
| Data + files | **Supabase** | Postgres + buckets `documents`, `user-templates` |

Branch mindset: `main` is production-ready; deploy backend/frontend from the release branch you intend to ship.

---

## Where secrets and env live

| Environment | Backend | Frontend |
|-------------|---------|----------|
| **Local** | `backend/.env` (copy from `.env.example`) | `frontend/.env.local` (copy from `.env.local.example`) |
| **Production** | Railway **Variables / Secrets** | Vercel **Environment Variables** |
| **Templates only (git)** | `backend/.env.example` | `frontend/.env.local.example` |

**Rules:**

- Never commit `.env` / `.env.local`.
- Never put `SUPABASE_SECRET_KEY`, LLM keys, `JWT_SECRET_KEY`, webhook secrets, or service-account JSON in the frontend — and never as `NEXT_PUBLIC_*`.
- Only `NEXT_PUBLIC_*` is browser-visible; treat it as public.
- Supabase project settings (schema, buckets, keys) live in the Supabase dashboard, not in git.

Settings are loaded in code from `backend/app/config.py` (Pydantic settings: `.env` + process env).

---

## Production mode

Set either:

- `APP_ENV=production` on Railway, **or**
- Railway’s built-in `RAILWAY_ENVIRONMENT=production`

Then:

- In-memory persistence is **rejected** (API / health fail closed).
- You **must** set real `SUPABASE_URL` + `SUPABASE_SECRET_KEY`.
- Keep `AUTH_ALLOW_EMAIL=false`.

Local/dev may omit Supabase and fall back to memory/disk. Production may not.

---

## Backend env (Railway)

Copy from [`backend/.env.example`](../backend/.env.example). Minimum for a working prod API:

| Variable | Required | Notes |
|----------|----------|-------|
| `APP_ENV` | Yes | `production` |
| `SUPABASE_URL` | Yes | Project URL |
| `SUPABASE_SECRET_KEY` | Yes | `sb_secret_…` — server only |
| `JWT_SECRET_KEY` | Yes | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `OPENAI_API_KEY` | Yes | Extraction |
| `GROQ_API_KEY` | Yes | Planner / refine |
| `CORS_ORIGINS` | Yes | Comma-separated Vercel origin(s), e.g. `https://your-app.vercel.app` |
| `GOOGLE_CLIENT_ID` | Yes (if Google sign-in) | Same value as frontend `NEXT_PUBLIC_GOOGLE_CLIENT_ID` |
| `AUTH_ALLOW_EMAIL` | Yes | `false` in prod |
| `PERSISTENCE_BACKEND` | Recommended | `auto` (or `supabase`) |
| `DOCUMENT_STORAGE` | Recommended | `auto` |
| `SUPABASE_DOCUMENTS_BUCKET` | Recommended | `documents` |
| `USER_TEMPLATE_STORAGE` | Recommended | `auto` |
| `SUPABASE_USER_TEMPLATES_BUCKET` | Recommended | `user-templates` |

Optional / feature flags:

| Variable | When |
|----------|------|
| `RESEND_API_KEY` / `RESEND_FROM_EMAIL` | Outbound email delivery |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Sheets export — users must share each spreadsheet with the JSON `client_email` as Editor (shown in Workflow Settings via `GET /api/integrations`) |
| `INBOUND_EMAIL_DOMAIN` / `INBOUND_WEBHOOK_SECRET` | Mailgun inbound — empty secret **rejects** all webhooks |
| `ADMIN_API_KEY` | Admin header routes |
| Rate limits / page caps | Defaults in `.env.example` are fine to start |

Full cheat sheet: [ARCHITECTURE.md §10](./ARCHITECTURE.md#10-keys--config-cheat-sheet).

---

## Rebrand / new cloud projects (Nexora)

You will eventually recreate vendor accounts under the **Nexora** name (new Google Cloud project, Supabase project, OAuth client, Resend domain, Mailgun domain). Until then, **current AgentFlow-named credentials are fine for local testing** — do not block ship work on renaming.

When you cut over:

1. **Google Cloud** — new project → OAuth Web client (`GOOGLE_CLIENT_ID` / `NEXT_PUBLIC_GOOGLE_CLIENT_ID`) + Sheets service account JSON (`GOOGLE_SERVICE_ACCOUNT_JSON`). Update Railway/Vercel + local `.env`. Users must re-share spreadsheets with the **new** `client_email` as Editor.
2. **Supabase** — new project → run schema/migrations + private buckets → swap `SUPABASE_URL` / `SUPABASE_SECRET_KEY` (and bucket names if changed).
3. **Resend** — new API key + verified sending domain (`RESEND_API_KEY` / `RESEND_FROM_EMAIL`).
4. **Mailgun (inbound)** — new receiving domain + webhook signing key (`INBOUND_EMAIL_DOMAIN` / `INBOUND_WEBHOOK_SECRET`) pointed at `POST /api/inbound/email`.
5. Smoke: `/api/health`, `/api/integrations` (shows Sheets share email), Google sign-in, one email send, one Sheets push, one inbound attachment if enabled.

### Integrations setup time & cost (ballpark)

| Piece | First-time setup | Ongoing cost (launch scale) |
|-------|------------------|-----------------------------|
| Google Sheets service account | ~15–30 min (create SA, enable Sheets API, download JSON, set env, restart) | **$0** — SA + Sheets API free for this use |
| Google OAuth (sign-in) | ~30–60 min (OAuth client, authorized origins) | **$0** |
| Resend outbound | ~30–60 min (account, API key; custom domain DNS longer) | **Free:** 3k emails/mo (100/day). Paid from ~$20/mo |
| Mailgun inbound | ~1–2 h (domain DNS MX/TXT, route → webhook, secret) | Often **pay-as-you-go** (no lasting free tier); small launch volume is low single-digit $/mo |
| Supabase project swap | ~1–2 h (schema, buckets, keys, migrate data if any) | Free tier usually enough early; paid when DB/storage grows |
| Full Nexora rebrand cutover (all of the above) | **~½–1 day** focused | Dominated by LLM spend (OpenAI/Groq), not Sheets/email |

**For testing now:** keep existing JSON path in `backend/.env`; restart API; Workflow Settings should show the share-as-Editor email from `/api/integrations`. No per-user JSON upload.

---

## Frontend env (Vercel)

From [`frontend/.env.local.example`](../frontend/.env.local.example):

| Variable | Notes |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Railway public HTTPS URL (no trailing slash issues — match how the client builds paths) |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Same OAuth Web client ID as backend `GOOGLE_CLIENT_ID` |
| `NEXT_PUBLIC_AUTH_ALLOW_EMAIL` | `false` in prod (must match backend) |
| `NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB` | Optional; default `10` |

After changing Vercel env, redeploy so the Next build picks them up.

---

## Supabase (data layer)

Not “env files” — dashboard + SQL:

1. Create project → run [`backend/supabase/schema.sql`](../backend/supabase/schema.sql) (or apply numbered migrations in order through at least `013_storage_private.sql`).
2. Seed templates if needed: `seed_templates.sql`.
3. Create **private** Storage buckets: `documents`, `user-templates` (or run `013_storage_private.sql`).
4. Copy **Project URL** + **secret key** into Railway.

Guide: [SUPABASE_SETUP.md](./SUPABASE_SETUP.md).

---

## How to deploy

### 1. Supabase

- Schema + migrations applied.
- Private buckets + storage policy.
- Keys ready for Railway.

### 2. Backend on Railway

1. New service from this repo (root or `backend/` per how you wire Docker).
2. Build with [`backend/Dockerfile`](../backend/Dockerfile) (`python:3.11-slim`, Tesseract, uvicorn on `:8000`).
3. Paste all backend variables (section above).
4. Deploy; confirm `GET /api/health` is healthy (not 503 for missing persistence).
5. First OCR/Docling traffic may download models — warm once before launch.

### 3. Frontend on Vercel

1. Import the repo; set root to `frontend/` (or monorepo settings accordingly).
2. Set `NEXT_PUBLIC_*` vars.
3. Deploy; open the site and confirm it hits the Railway API.

### 4. Align auth + CORS

- Google Cloud OAuth client: authorized JavaScript origins / redirect URIs include the production frontend origin.
- `CORS_ORIGINS` on Railway includes that same origin (and any custom domain).
- Backend `GOOGLE_CLIENT_ID` ≡ frontend `NEXT_PUBLIC_GOOGLE_CLIENT_ID`.

### 5. Custom domain (optional)

- Point domain at Vercel; add the same origin to `CORS_ORIGINS` and Google OAuth.
- Railway custom domain for a stable API URL if you do not want the default `*.up.railway.app`.

---

## Smoke test after deploy

1. `GET /api/health` → OK.
2. Sign in (Google) → session token stored; `GET /api/users/me` works.
3. Upload → adhoc or template run → poll until complete.
4. Second user cannot `GET` that run → **403**.
5. Hit a rate/usage limit path if configured → **429** / clear UI copy.
6. Optional: email / Sheets / inbound webhook with secrets set.

More checks: section **Smoke test after deploy** above.

---

## Local vs production

| | Local | Production |
|--|-------|------------|
| Env files | `.env` / `.env.local` on disk | Host dashboards only |
| Persistence | Memory OK if Supabase unset | Supabase required |
| Document storage | Local disk or Supabase | Supabase Storage (private) |
| `AUTH_ALLOW_EMAIL` | May be `true` for testing | `false` |
| `CORS_ORIGINS` | `http://localhost:3000` | Real Vercel / custom domain |

---

## Related docs

| Doc | Use |
|-----|-----|
| [NEXT-STEPS.md](./NEXT-STEPS.md) | Current ship order (deploy is ~step 2) |
| [SUPABASE_SETUP.md](./SUPABASE_SETUP.md) | DB + Storage setup |
| [ARCHITECTURE.md §14](./ARCHITECTURE.md#14-deployment-sketch) | Mermaid sketch |
| [SCALING-AND-JOBS.md](./SCALING-AND-JOBS.md) | Later: queues, multi-replica |
