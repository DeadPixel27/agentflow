# AgentFlow - Project Spec

**One-liner:** Describe what you want done with your documents -> system builds and runs an AI agent pipeline automatically.

> **Progress snapshot (2026-08-07):** MVP + pre-deploy hardening + template library + **V1.3 chat refinement** + **versioned user templates** shipped on `develop`. Supabase verified (Postgres + `Documents` + `user-templates` buckets). **62 backend tests passing.** Master template owner-apply deferred. See [ARCHITECTURE.md](./ARCHITECTURE.md) for system diagrams.

**Documentation:** All markdown lives in repo root, `docs/`, and `backend/` — see [docs/README.md](./docs/README.md). Screenshot JPEGs under `docs/_archive/source-screenshots/` are gitignored.

---

## What It Does

1. User uploads documents (PDFs, images, scanned files)
2. User describes the task in plain English: *"Extract vendor name, invoice number, amount, and date. Flag anything over ₹50K. Give me a CSV."*
3. User picks a **template** or describes a custom task in plain English
4. System plans a pipeline (template = deterministic plan; custom = LLM planner)
5. Each agent executes its step (OCR → Extract → Rules → Format)
6. User watches progress in real-time and downloads results

---

## MVP Scope (2-3 weeks)

### Core Features

- [x] Upload 1-10 documents (PDF, PNG, JPG)
- [x] Template picker on landing page (7 presets → `POST /api/runs/template`)
- [x] Text input: describe what you want extracted/done (→ `POST /api/runs/adhoc`)
- [x] Planner agent: breaks task into steps automatically
- [x] Pipeline execution: runs each agent step sequentially (async background runs)
- [x] Real-time status updates in UI (poll `GET /api/runs/{id}` every 1.5s)
- [x] Results view: structured table + download CSV/JSON
- [x] Pipeline history: expandable run history per workflow (input docs + output)
- [x] Save workflow from a run and rerun on new uploads
- [x] Chat refinement on results page (`POST /api/runs/{id}/refine`)
- [x] Template version history + branch/revert (run and workflow scope)
- [x] Email-based sign-in (restores same Supabase user + workflows)

### Available Agent Types (v1)

| Agent | What it does | Status |
|-------|--------------|--------|
| **OCR Agent** | Converts images/scanned PDFs to text (Tesseract) | ✅ `processor.ocr` |
| **Text Extractor** | Pulls raw text from digital PDFs (PyMuPDF) | ✅ `processor.text_extract` |
| **Field Extractor** | LLM extracts structured fields from text based on user description | ✅ `transform.field_extractor` |
| **Rules Agent** | Applies user-defined conditions (flag if amount > X, filter by date, etc.) | ✅ `transform.rules` |
| **Formatter Agent** | Compiles results into CSV/JSON/table format | ✅ `output.formatter` |

> **Note:** All 5 agents are implemented and registered. Rules is used when the task mentions flags/conditions (e.g. "flag over 50K").

### Planner Logic

User input + document sample -> LLM decides which agents to run and in what order.

**Example:**

```
User: "Extract name, email, and phone from these resumes"
Documents: 5 PDFs

Planner output:
Step 1: Text Extractor (digital PDFs detected)
Step 2: Field Extractor (fields: name, email, phone)
Step 3: Formatter (output: CSV)
```

**Another example:**

```
User: "Pull invoice amounts, flag anything over 50K, give me Excel"
Documents: 10 scanned images

Planner output:
Step 1: OCR Agent (scanned images detected)
Step 2: Field Extractor (fields: invoice_number, vendor, amount, date)
Step 3: Rules Agent (flag: amount > 50000)
Step 4: Formatter (output: CSV with flag column)
```

---

## Tech Stack

| Layer | Tool | Why | Status |
|-------|------|-----|--------|
| **Frontend** | Next.js 14 + TypeScript + Tailwind CSS | Learn remote-job stack by building | ✅ Done |
| **UI Components** | shadcn/ui | Modern, clean, fast to implement | ✅ Done |
| **Backend** | Python 3.9 + FastAPI | Async API, clean service layer | ✅ Done |
| **AI (Planner)** | Groq (Llama 3.3) | Free tier; replaced original OpenAI plan | ✅ Done |
| **AI (Agents)** | Groq (Llama 3.3) – free tier | Fast, free, good for extraction tasks | ✅ Done |
| **OCR** | Tesseract (pytesseract) | Free, local, no API cost | ✅ Done (needs `brew install tesseract`) |
| **PDF parsing** | PyMuPDF (fitz) | Free, fast, extracts text from digital PDFs | ✅ Done |
| **Database** | Supabase (Postgres) | Users, workflows, runs | ✅ Done (auto fallback to in-memory) |
| **File storage** | Supabase Storage | Uploaded documents | ✅ Done (auto fallback to local disk) |
| **Auth** | Email lookup (no password) | MVP session; future: Supabase Auth | ✅ Done |
| **Deploy (frontend)** | Vercel | Free for personal projects | ❌ Not started |
| **Deploy (backend)** | Railway | $5 free credit/month | ❌ Not started |
| **Pre-deploy hardening** | CORS, rate limits, MIME, Dockerfile, etc. | See local `docs/GAPS-TECHNICAL.md` | ✅ Done |
| **Templates** | Code-defined presets + Supabase mirror | `backend/app/templates/` | ✅ Done |
| **User template versions** | Supabase Storage `user-templates` + Postgres index | Refined plans per run/workflow | ✅ Done |
| **Code** | GitHub (public repo) | Recruiters will see this | ✅ [kabirrao2002/agentflow](https://github.com/kabirrao2002/agentflow) |

---

## Architecture

Full diagrams (system context, three-layer templates, pipeline flow, persistence registry): **[ARCHITECTURE.md](./ARCHITECTURE.md)**

```
┌─────────────────────────────────────────────────────────┐
│              Next.js Frontend (localhost:3000)           │
│  /  upload + task    /results/[id]  poll + refine        │
│  /workflows          /account       version history      │
└──────────────────────────┬──────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────┐
│                   FastAPI Backend                          │
│  routes → Depends() → services → registry → backends     │
│  Planner │ Runner │ RefineService │ VersionService       │
│  Agent Registry + pipeline_refiner (chat refine)         │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│   Supabase Postgres + Storage                            │
│   Tables: users, workflows, runs, user_template_versions │
│   Buckets: Documents (uploads), user-templates (versions)│
└───────────────────────────────────────────────────────────┘
```

See also: [ARCHITECTURE.md](./ARCHITECTURE.md), `backend/DOCUMENT_STORAGE.md`, `frontend/FRONTEND.md`

---

## Pages (Frontend)

### 1. Landing Page (`/`)

- [x] Hero: "Describe your task. Upload documents. AI does the rest."
- [x] Template picker grid (invoice, resume, contract, …)
- [x] Upload zone (drag & drop)
- [x] Text input for task description + example task chips
- [x] "Run Pipeline" button → redirects to results

### 2. Results Page (`/results/[runId]`)

- [x] Live step cards with progress bar (queued → running → done / failed)
- [x] Expandable steps: config, reason, output JSON
- [x] Table view of extracted/processed data
- [x] Download buttons: CSV, JSON
- [x] Summary stats (documents, rows, steps, flags)
- [x] Save as workflow
- [x] Chat refine panel (`refine-chat.tsx`)
- [x] Template version history + branch from earlier version

### 3. Workflows (`/workflows`, `/workflows/[workflowId]`)

- [x] List saved workflows
- [x] Workflow detail with rerun panel
- [x] Expandable run history (input docs + output download)
- [x] Template version panel + "Using vN" badge
- [x] Revert workflow head for next rerun

### 4. Account (`/account`)

- [x] Sign in / create account by email
- [x] Sign out (clears localStorage session)
- [x] Same email restores workflows from Supabase

---

## API Endpoints (Backend)

### Core

| Method | Endpoint | What it does | Status |
|--------|----------|--------------|--------|
| GET | `/api/health` | Health + active backends | ✅ |
| POST | `/api/upload` | Upload documents, returns upload_id | ✅ |
| GET | `/api/uploads/{id}` | List documents in upload batch | ✅ |
| GET | `/api/uploads/{id}/documents/{doc_id}` | Download input document | ✅ |
| POST | `/api/pipeline/create` | Plan pipeline from task + upload | ✅ |
| GET | `/api/templates` | List pipeline templates (summary: id, name, icon, category) | ✅ |
| GET | `/api/templates/{id}` | Get full template (fields, rules, extraction_instructions) | ✅ |
| POST | `/api/runs/adhoc` | Plan + start run (background) | ✅ |
| POST | `/api/runs/template` | Run from template id (deterministic plan) | ✅ |
| POST | `/api/runs` | Run explicit steps (background) | ✅ |
| GET | `/api/runs/{id}` | Poll run status + results | ✅ |
| POST | `/api/runs/{id}/refine` | Chat refine → child run | ✅ |
| GET | `/api/runs/{id}/template-versions` | List run template versions | ✅ |
| GET | `/api/runs/{id}/template-versions/{version_id}` | Preview version | ✅ |
| POST | `/api/runs/{id}/revert` | Branch from version → new run | ✅ |

### Auth & Users

| Method | Endpoint | What it does | Status |
|--------|----------|--------------|--------|
| POST | `/api/auth/session` | Sign in or register by email | ✅ |
| POST | `/api/users` | Create/restore user (delegates to auth) | ✅ |
| GET | `/api/users/{id}` | Get user | ✅ |
| GET | `/api/users/{id}/workflows` | List user's workflows | ✅ |

### Workflows

| Method | Endpoint | What it does | Status |
|--------|----------|--------------|--------|
| POST | `/api/workflows` | Save workflow template | ✅ |
| POST | `/api/workflows/from-run/{id}` | Save plan from a run | ✅ |
| GET | `/api/workflows/{id}` | Get workflow + steps | ✅ |
| GET | `/api/workflows/{id}/runs` | List all runs for a workflow | ✅ |
| POST | `/api/workflows/{id}/runs` | Rerun saved workflow (seeds run-scope v1) | ✅ |
| GET | `/api/workflows/{id}/template-versions` | List workflow template versions | ✅ |
| GET | `/api/workflows/{id}/template-versions/{version_id}` | Preview workflow version | ✅ |
| POST | `/api/workflows/{id}/revert` | Set workflow head to earlier version | ✅ |

### Admin (owner — deferred)

| Method | Endpoint | What it does | Status |
|--------|----------|--------------|--------|
| GET | `/api/admin/templates/feedback` | List user refinement events | ✅ |
| POST | `/api/admin/templates/{id}/synthesize` | LLM synthesis from user feedback | ✅ |
| POST | `/api/admin/templates/{id}/preview` | Preview master template changes | ✅ |
| POST | `/api/admin/templates/{id}/apply` | Persist master template changes | ⬜ later (`ADMIN_API_KEY`) |

### Debug

| Method | Endpoint | What it does | Status |
|--------|----------|--------------|--------|
| POST | `/api/extract` | Extract from raw text | ✅ |

---

## Backend Architecture Patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| **Protocol** (interface) | `persistence/protocols.py`, `services/auth/protocols.py` | Contracts for backends |
| **Registry** (wiring) | `persistence/registry.py`, `services/auth/registry.py` | Config → implementation |
| **FastAPI Depends** | `api/dependencies.py` | Inject services into routes |
| **Service classes** | `users/`, `workflows/`, `templates/`, `pipeline/` | Business logic |
| **Version service** | `UserTemplateVersionService` | Run/workflow template payloads in Storage |
| **Template catalog** | `app/templates/` + `persistence/templates/` | Code-defined presets; DB mirror via bootstrap |
| **Validation utils** | `validation/task_input.py` | Task sanitization (no Pydantic → services import) |
| **Domain errors** | `models/domain/document.py` | `InvalidUploadError` etc.; routes map to HTTP |

See [docs/ENGINEERING-PRINCIPLES.md](./docs/ENGINEERING-PRINCIPLES.md) for coding rules. Adding a new storage backend (e.g. S3): one file + one line in `registry.py` + env var.

---

## Database Schema

> Implemented in `backend/supabase/schema.sql`. Seed templates via `supabase/seed_templates.sql`.

| Table | Purpose |
|-------|---------|
| `users` | `id`, `name`, `email` (indexed; used for sign-in lookup) |
| `workflows` | Saved pipeline templates per user |
| `workflow_steps` | Steps belonging to a workflow |
| `workflow_runs` | Execution records (status, result JSON, planned_steps) |
| `workflow_step_runs` | Per-step status + output during a run |
| `pipeline_templates` | Editable task presets (landing page; not user workflows) |
| `user_template_versions` | Metadata index for run/workflow template versions |
| `refinement_events` | User refine messages (owner aggregation) |

Document files are stored in **Supabase Storage** (`Documents` bucket), not in Postgres.

## Environment Variables

### Backend (`backend/.env`)

```env
GROQ_API_KEY=...
SUPABASE_URL=...
SUPABASE_SECRET_KEY=...
PERSISTENCE_BACKEND=auto        # auto | memory | supabase
DOCUMENT_STORAGE=auto           # auto | local | supabase
SUPABASE_DOCUMENTS_BUCKET=Documents   # must match bucket name exactly (case-sensitive)
AUTH_BACKEND=email              # email | supabase (future)
CORS_ORIGINS=http://localhost:3000    # comma-separated; set prod URL on deploy
RATE_LIMIT_RUNS_ADHOC=10/minute
RATE_LIMIT_UPLOAD=20/minute
MAX_UPLOAD_SIZE_MB=10
```

### Frontend (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB=10
```

---

## Build Plan

### Week 1: Backend + Core Pipeline ✅

- [x] FastAPI project, upload, OCR, PDF extraction
- [x] Planner + all 5 agents + unified registry
- [x] Pipeline runner with async background execution + incremental step saves
- [x] Supabase persistence (optional in-memory fallback)
- [x] Workflows, users, run history
- [x] Persistence registry (Protocol + swappable backends)
- [x] Document storage registry (local / Supabase Storage)
- [x] FastAPI Depends service injection
- [x] Email auth service (strategy pattern)
- [x] Landing page template picker + `runTemplate()` API
- [x] 38 backend tests passing
- [x] Local planning docs in `docs/` (gitignored)

### Week 2: Frontend ✅

- [x] Next.js 14 + TypeScript + Tailwind + shadcn/ui
- [x] Landing page with hero, examples, upload + run
- [x] Results page with polling, expandable steps, CSV/JSON download
- [x] Workflows list + detail + rerun + expandable run history
- [x] Account page with email sign-in
- [x] Mobile nav, toasts, empty states
- [x] `frontend/FRONTEND.md` directory guide
- [x] E2E tested locally
- [x] PR #2 merged to `develop`

### Week 3: Pre-deploy hardening ✅ (merged PR #3 → `develop` → `main`)

- [x] CORS from `CORS_ORIGINS` env var
- [x] Rate limiting (`slowapi` on adhoc + upload + template runs)
- [x] Prompt injection guard (`validation/task_input.py`)
- [x] MIME validation (`filetype` byte sniffing)
- [x] Per-file + batch file size limits
- [x] LLM retry (`tenacity` on Groq client)
- [x] Shared `to_planned_steps()` mapper
- [x] `InvalidUploadError` domain exception
- [x] Backend `Dockerfile` + `.dockerignore`
- [x] Frontend `error.tsx` error boundary
- [x] Code-defined templates (`backend/app/templates/`) + `POST /api/runs/template`
- [x] Merged to `develop` and `main` (`800cc03`)

### Week 4: Deploy + Demo ❌ (current focus)

- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Vercel
- [ ] Set production env vars + `CORS_ORIGINS`
- [ ] End-to-end smoke test on live URLs
- [ ] Record 60-sec demo video
- [ ] Root README with screenshots + live demo link
- [ ] Add to LinkedIn / resume
- [x] Merge `develop` → `main` for release (`800cc03`)

---

## Master Tracker

> **Single source of truth for open work.** Extended notes: [docs/GAPS-TECHNICAL.md](./docs/GAPS-TECHNICAL.md), [docs/PLAN-AND-NEXT-STEPS.md](./docs/PLAN-AND-NEXT-STEPS.md), [docs/FEATURE-ROADMAP.md](./docs/FEATURE-ROADMAP.md).

### Gap priority (from code review)

| # | Task | Time | Impact | Status |
|---|------|------|--------|--------|
| 1 | Fix CORS (env var) | 10 min | Deploy blocker | ✅ |
| 2 | Add rate limiting | 30 min | Cost protection | ✅ |
| 3 | Add Dockerfile | 15 min | Deploy blocker | ✅ |
| 4 | Add prompt injection guard | 30 min | Security | ✅ |
| 5 | Add LLM retry | 20 min | Reliability | ✅ |
| 6 | Fix code duplication (`to_planned_steps`) | 10 min | Code quality | ✅ |
| 7 | Add error boundary | 15 min | UX | ✅ |
| 8 | Add file cleanup (24h TTL) | 1–2 hr | Privacy + cost | ⬜ |
| 9 | Add auth (Supabase Auth) | 3–4 hr | Security | ⬜ |
| 10 | Add file content validation (`filetype`) | 30 min | Security | ✅ |

**Total remaining to production-ready:** ~2–4 hours (deploy + optional auth/cleanup).

### Feature timeline (post-MVP)

| Version | Feature | Effort | Doc |
|---------|---------|--------|-----|
| V1.0.1 | Template library (picker + API) | ~3 hr | ✅ Done — `backend/app/templates/` |
| V1.1 | Email delivery (Resend) | Medium | `docs/FEATURE-ROADMAP.md` |
| V1.2 | Google Sheets push | Medium | `docs/FEATURE-ROADMAP.md` |
| V1.3 | Chat refinement + versioned user templates | High | ✅ Done — [CHAT-REFINEMENT.md](./docs/CHAT-REFINEMENT.md), [ARCHITECTURE.md](./ARCHITECTURE.md) |
| V2.0 | Live PDF preview + field highlights | 6–10 hr | `docs/FEATURE-ROADMAP.md` |
| V2.0 | Auto-correct / learning from edits | Medium | `docs/FEATURE-ROADMAP.md` |
| V3.0 | Watch folder / inbox automation | 12–20 hr | `docs/FEATURE-ROADMAP.md` |

### Phase A — Deploy (P0)

| Status | Task | Doc |
|--------|------|-----|
| [x] | CORS from env var | [GAPS #3](./GAPS-TECHNICAL.md) |
| [x] | Backend Dockerfile | [GAPS #9](./GAPS-TECHNICAL.md) |
| [ ] | Deploy backend (Railway) + env vars | `docs/PLAN-AND-NEXT-STEPS.md` |
| [ ] | Deploy frontend (Vercel) + `NEXT_PUBLIC_API_URL` | `docs/PLAN-AND-NEXT-STEPS.md` |
| [ ] | Live smoke test (upload → template run → download) | `docs/PLAN-AND-NEXT-STEPS.md` |
| [ ] | README screenshots + live demo URL | `docs/PLAN-AND-NEXT-STEPS.md` |
| [ ] | 60-sec demo video | `docs/PLAN-AND-NEXT-STEPS.md` |

### Phase B — Security & reliability (P1)

| Status | Task | Doc |
|--------|------|-----|
| [x] | Rate limiting on `/api/runs/adhoc`, `/api/runs/template`, `/api/upload` | ✅ |
| [x] | Prompt injection guard | [GAPS #4](./GAPS-TECHNICAL.md) |
| [x] | MIME validation (`filetype`) | [GAPS #5](./GAPS-TECHNICAL.md) |
| [x] | File size limits (per-file + batch) | [GAPS #5](./GAPS-TECHNICAL.md) |
| [x] | LLM retry (429 / 5xx) | [GAPS #6](./GAPS-TECHNICAL.md) |
| [x] | Frontend error boundary | [GAPS #10](./GAPS-TECHNICAL.md) |
| [x] | Dedupe `_to_planned_steps()` | [GAPS #7](./GAPS-TECHNICAL.md) |
| [x] | Merge pre-deploy work to `develop` and `main` | PR #3, `800cc03` |

### Phase C — Ops & quality (P2)

| Status | Task | Doc |
|--------|------|-----|
| [ ] | GitHub Actions CI (`pytest` + `npm run build`) | [GAPS #12](./GAPS-TECHNICAL.md) |
| [ ] | Upload file cleanup (24h TTL sweep) | [GAPS #8](./GAPS-TECHNICAL.md) |
| [ ] | System prompts in config/files | [GAPS #15](./GAPS-TECHNICAL.md) |
| [ ] | Frontend tests (Vitest) | [GAPS #14](./GAPS-TECHNICAL.md) |
| [ ] | Usage metering (Groq tokens per run) | [GAPS #13](./GAPS-TECHNICAL.md) |

### Phase D — Auth (before public launch)

| Status | Task | Doc |
|--------|------|-----|
| [ ] | Supabase Auth provider (password / magic link) | [GAPS #1](./GAPS-TECHNICAL.md) |
| [ ] | Frontend Supabase JS sign-in/sign-up | [GAPS #1](./GAPS-TECHNICAL.md) |
| [ ] | Keep `email` provider for local dev/tests | [GAPS #1](./GAPS-TECHNICAL.md) |

### Phase E — Template library (V1.0.1) ✅

**Code canonical:** `backend/app/templates/` (7 modules) → `registry.py` → repos + bootstrap SQL sync.

| Status | Task | Doc |
|--------|------|-----|
| [x] | `backend/app/templates/` Python modules (invoice, resume, contract, …) | `app/templates/` |
| [x] | Rich templates: `fields`, `extraction_instructions`, `rules`, `output_format` | `app/templates/` |
| [x] | `TemplateRepository` — code registry at runtime | `persistence/templates/` |
| [x] | `GET /api/templates` + `GET /api/templates/{id}` | API |
| [x] | `POST /api/runs/template` — deterministic plan from template | API |
| [x] | Inject `extraction_instructions` into field extractor config | `template_planner.py` |
| [x] | Landing page template picker + `runTemplate()` when selected | Frontend |
| [x] | `pipeline_templates` table + seed SQL (DB mirror) | `supabase/seed_templates.sql` |
| [x] | Bootstrap syncs code templates to Supabase on startup | `bootstrap.py` |
| [x] | Run `setup_templates.sql` in Supabase | User completed |
| [ ] | Category filter UI (API supports `?category=`) | optional V1.0.2 |

### Phase I — Versioned user templates (V1.3) ✅

| Status | Task | Doc |
|--------|------|-----|
| [x] | Three-layer model: master → run versions → workflow versions | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| [x] | `user_template_versions` + `refinement_events` tables (migration 007) | `supabase/migrations/007_*.sql` |
| [x] | Supabase Storage bucket `user-templates` for payloads | [SUPABASE_SETUP.md](./backend/SUPABASE_SETUP.md) |
| [x] | `POST /api/runs/{id}/refine` + version pointer dedup in Postgres | API |
| [x] | List / preview / revert APIs (run + workflow scope) | `template_versions.py` |
| [x] | Frontend version panel + workflow refresh + scope labels | Frontend |
| [x] | Workflow rerun seeds run-scope v1 for results history | `WorkflowService.start_workflow_run` |
| [ ] | Owner master template apply (`ADMIN_API_KEY`) | deferred |

### Phase F — Product features (V1.1+)

| Status | Version | Feature | Doc |
|--------|---------|---------|-----|
| [ ] | V1.1 | Email delivery (Resend) — `output.email` agent | [FEATURE-ROADMAP](./FEATURE-ROADMAP.md) |
| [ ] | V1.2 | Google Sheets push — `output.google_sheets` | [FEATURE-ROADMAP](./FEATURE-ROADMAP.md) |
| [x] | V1.3 | Chat refinement on results — `POST /api/runs/{id}/refine` | [CHAT-REFINEMENT.md](./CHAT-REFINEMENT.md) |
| [ ] | V2.0 | Live PDF preview + field highlights | [FEATURE-ROADMAP](./FEATURE-ROADMAP.md) |
| [ ] | V2.0 | Auto-correct / learning from user edits | [FEATURE-ROADMAP](./FEATURE-ROADMAP.md) |
| [ ] | V3.0 | Watch folder / inbox automation | [FEATURE-ROADMAP](./FEATURE-ROADMAP.md) |

### Phase G — New agents (planned)

| Status | Agent type | Version | Doc |
|--------|------------|---------|-----|
| [ ] | `output.email` | V1.1 | [AGENTS.md](./AGENTS.md) |
| [ ] | `output.google_sheets` | V1.2 | [AGENTS.md](./AGENTS.md) |
| [ ] | `transform.summarizer` | V1.3 | [AGENTS.md](./AGENTS.md) |
| [ ] | `transform.classifier` | V2.0 | [AGENTS.md](./AGENTS.md) |
| [ ] | `processor.table_extract` | V2.0 | [AGENTS.md](./AGENTS.md) |
| [ ] | `transform.redact` | V2.0 | [AGENTS.md](./AGENTS.md) |
| [ ] | `output.webhook` | V2.0 | [AGENTS.md](./AGENTS.md) |
| [ ] | `processor.translate` | V3.0 | [AGENTS.md](./AGENTS.md) |
| [ ] | `trigger.watch_folder` | V3.0 | [AGENTS.md](./AGENTS.md) |

### Phase H — Infrastructure & polish

| Status | Task | Doc |
|--------|------|-----|
| [ ] | SSE / WebSockets for run status (replace polling) | [GAPS #11](./GAPS-TECHNICAL.md) |
| [ ] | S3 document backend (registry ready) | SPEC Future |
| [ ] | `global-error.tsx` (optional) | [GAPS #10](./GAPS-TECHNICAL.md) |
| [x] | Chat refinement: cache OCR text on run for partial re-run | [CHAT-REFINEMENT.md](./CHAT-REFINEMENT.md) |
| [x] | Chat refinement: `parent_run_id` lineage column | [CHAT-REFINEMENT.md](./CHAT-REFINEMENT.md) |

### Completed (reference)

<details>
<summary>MVP + docs + hardening (click to expand)</summary>

- [x] All 5 v1 agents + planner + async runner
- [x] Supabase Postgres + Storage (with in-memory/local fallback)
- [x] Persistence + auth registry, FastAPI Depends
- [x] Full Next.js frontend (/, results, workflows, account)
- [x] Email sign-in, workflow save/rerun, run history
- [x] Docs transcribed from screenshots: ENGINEERING-PRINCIPLES, GAPS-TECHNICAL, TEMPLATES, AGENTS, CHAT-REFINEMENT, FEATURE-ROADMAP, PROMPTS, README (+ MARKET-ANALYSIS stub)
- [x] Template library (code-defined, 7 templates, `POST /api/runs/template`)
- [x] Versioned user templates (Storage + branch/revert APIs, 62 tests)

</details>

---

### Future (quick reference)

Legacy list — see [Master Tracker](#master-tracker) for live status.

- [ ] Supabase Auth (password / magic link) — Phase D
- [ ] SSE/WebSockets instead of polling — Phase H
- [ ] S3 document backend — Phase H

---

## Cost

| Item | Monthly cost |
|------|--------------|
| Groq (planner + agents) | $0 (free tier) |
| Tesseract OCR | $0 (local) |
| Railway (backend) | $0-5 |
| Vercel (frontend) | $0 |
| Supabase (DB + storage) | $0 |
| **Total** | **~$0-5/month** |

---

## What This Proves To Employers

1. **System design** — multi-agent pipeline, registry pattern, swappable backends — ✅
2. **AI/LLM integration** — planner + extraction via Groq API — ✅
3. **Python backend** — FastAPI, async runs, Depends DI, Protocol interfaces — ✅
4. **Frontend** — Next.js, TypeScript, polling, workflows UI — ✅
5. **Full-stack deployment** — live demo — ❌ not yet (Phase A)
6. **Document processing** — OCR, PDF parsing, structured extraction — ✅
7. **Database design** — normalized schema + JSONB + Supabase Storage — ✅

This is not a tutorial project. This is production-level architecture on a public repo.

---

*Created: 2026-08-02*  
*Updated: 2026-08-07 — V1.3 versioned templates; docs + ARCHITECTURE.md on GitHub*
