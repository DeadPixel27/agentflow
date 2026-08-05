# AgentFlow - Project Spec

**One-liner:** Describe what you want done with your documents -> system builds and runs an AI agent pipeline automatically.

> **Progress snapshot (2026-08-05):** Full-stack MVP complete on `develop`. Backend + Next.js frontend E2E tested locally with Supabase (Postgres + Storage). PR #2 merged. Production deploy, README polish, and demo video not started yet.

---

## What It Does

1. User uploads documents (PDFs, images, scanned files)
2. User describes the task in plain English: *"Extract vendor name, invoice number, amount, and date. Flag anything over ₹50K. Give me a CSV."*
3. System plans a multi-step agent pipeline automatically
4. Each agent executes its step (OCR -> Extract -> Validate -> Format)
5. User watches progress in real-time and downloads results

---

## MVP Scope (2-3 weeks)

### Core Features

- [x] Upload 1-10 documents (PDF, PNG, JPG)
- [x] Text input: describe what you want extracted/done
- [x] Planner agent: breaks task into steps automatically
- [x] Pipeline execution: runs each agent step sequentially (async background runs)
- [x] Real-time status updates in UI (poll `GET /api/runs/{id}` every 1.5s)
- [x] Results view: structured table + download CSV/JSON
- [x] Pipeline history: expandable run history per workflow (input docs + output)
- [x] Save workflow from a run and rerun on new uploads
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
| **Code** | GitHub (public repo) | Recruiters will see this | ✅ [kabirrao2002/agentflow](https://github.com/kabirrao2002/agentflow) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Next.js Frontend (localhost:3000)           │
│  /  upload + task    /results/[id]  poll + table        │
│  /workflows          /account       email sign-in       │
└──────────────────────────┬──────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────┐
│                   FastAPI Backend                          │
│  routes → Depends() → services → registry → backends     │
│  ┌────────────┐  ┌──────────┐  ┌─────────────────────┐   │
│  │ AuthService│  │ Planner  │  │ Pipeline Runner     │   │
│  │ (email)    │  │ (Groq)   │  │ (async + step save) │   │
│  └────────────┘  └──────────┘  └─────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Agent Registry: OCR │ Extract │ Rules │ Format      │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌──────────────────────┐  ┌──────────────────────────┐  │
│  │ persistence/registry │  │ documents/registry       │  │
│  │ memory / supabase    │  │ local / supabase storage │  │
│  └──────────────────────┘  └──────────────────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│   Supabase: Postgres (users, workflows, runs)             │
│             Storage bucket `Documents` (uploaded files)   │
└───────────────────────────────────────────────────────────┘

Session: browser localStorage holds user_id after sign-in.
Data: always in Supabase when configured.
```

See also: `backend/DOCUMENT_STORAGE.md`, `frontend/FRONTEND.md`

---

## Pages (Frontend)

### 1. Landing Page (`/`)

- [x] Hero: "Describe your task. Upload documents. AI does the rest."
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

### 3. Workflows (`/workflows`, `/workflows/[workflowId]`)

- [x] List saved workflows
- [x] Workflow detail with rerun panel
- [x] Expandable run history (input docs + output download)

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
| POST | `/api/runs/adhoc` | Plan + start run (background) | ✅ |
| POST | `/api/runs` | Run explicit steps (background) | ✅ |
| GET | `/api/runs/{id}` | Poll run status + results | ✅ |

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
| POST | `/api/workflows/{id}/runs` | Rerun saved workflow | ✅ |

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
| **Service classes** | `users/`, `workflows/`, `auth/`, `documents/` | Business logic |

Adding a new storage backend (e.g. S3): one file + one line in `registry.py` + env var.

---

## Database Schema

> Implemented in `backend/supabase/schema.sql`. Tables: `users`, `workflows`, `workflow_steps`, `workflow_runs`, `workflow_step_runs`.

| Table | Purpose |
|-------|---------|
| `users` | `id`, `name`, `email` (indexed; used for sign-in lookup) |
| `workflows` | Saved pipeline templates per user |
| `workflow_steps` | Steps belonging to a workflow |
| `workflow_runs` | Execution records (status, result JSON, planned_steps) |
| `workflow_step_runs` | Per-step status + output during a run |

Document files are stored in **Supabase Storage** (`Documents` bucket), not in Postgres.

---

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
```

### Frontend (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
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
- [x] 19 backend tests passing

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

### Week 3: Deploy + Demo ❌ (next)

- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Vercel
- [ ] Set production env vars + CORS
- [ ] End-to-end smoke test on live URLs
- [ ] Record 60-sec demo video
- [ ] Root README with screenshots + architecture
- [ ] Add to LinkedIn / resume

### Future (post-MVP)

- [ ] Supabase Auth (password / magic link) — replace email-only provider
- [ ] SSE/WebSockets instead of polling
- [ ] S3 document backend (registry ready)
- [ ] Merge `develop` → `main` for release

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
5. **Full-stack deployment** — live demo — ❌ not yet
6. **Document processing** — OCR, PDF parsing, structured extraction — ✅
7. **Database design** — normalized schema + JSONB + Supabase Storage — ✅

This is not a tutorial project. This is production-level architecture on a public repo.

---

*Created: 2026-08-02*  
*Updated: 2026-08-05*
