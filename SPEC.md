# AgentFlow - Project Spec

**One-liner:** Describe what you want done with your documents -> system builds and runs an AI agent pipeline automatically.

> **Progress snapshot (2026-08-04):** Backend MVP is largely complete and manually tested end-to-end. Frontend, auth, and production deploy are not started yet.

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
- [x] Text input: describe what you want extracted/done *(API only — `POST /api/runs/adhoc`)*
- [x] Planner agent: breaks task into steps automatically
- [x] Pipeline execution: runs each agent step sequentially
- [ ] Real-time status updates in UI (step 1/4 running... done)
- [ ] Results view: structured table + download CSV/JSON *(API returns results; no UI yet)*
- [x] Pipeline history: see past runs *(API: `GET /api/runs/{id}`, `GET /api/workflows/{id}/runs` — no UI yet)*

### Available Agent Types (v1)

| Agent | What it does | Status |
|-------|--------------|--------|
| **OCR Agent** | Converts images/scanned PDFs to text (Tesseract) | ✅ `processor.ocr` |
| **Text Extractor** | Pulls raw text from digital PDFs (PyMuPDF) | ✅ `processor.text_extract` |
| **Field Extractor** | LLM extracts structured fields from text based on user description | ✅ `transform.field_extractor` |
| **Rules Agent** | Applies user-defined conditions (flag if amount > X, filter by date, etc.) | ✅ `transform.rules` |
| **Formatter Agent** | Compiles results into CSV/JSON/table format | ✅ `output.formatter` |

> **Note:** All 5 agents are implemented and registered. Your resume test used `field_extractor` → `formatter` (no rules step needed). Rules is used when the task mentions flags/conditions (e.g. "flag over 50K").

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
| **Frontend** | Next.js 14 + TypeScript + Tailwind CSS | Learn remote-job stack by building | ❌ Not started |
| **UI Components** | shadcn/ui | Modern, clean, fast to implement | ❌ Not started |
| **Backend** | Python 3.12 + FastAPI | Strongest language, best async support | ✅ Done (Python 3.9 venv) |
| **AI (Planner)** | OpenAI GPT-4o-mini | Smart enough to plan, cheap enough to run | ⚠️ Using **Groq** instead (free tier) |
| **AI (Agents)** | Groq (Llama 3) – free tier | Fast, free, good for extraction tasks | ✅ Done |
| **OCR** | Tesseract (pytesseract) | Free, local, no API cost | ✅ Done (needs `brew install tesseract`) |
| **PDF parsing** | PyMuPDF (fitz) | Free, fast, extracts text from digital PDFs | ✅ Done |
| **Database** | Supabase (Postgres) | Free tier, stores pipeline runs + results | ⚠️ Code ready; optional — falls back to in-memory |
| **File storage** | Supabase Storage | Free tier, stores uploaded documents | ❌ Using local disk (`uploads/`) |
| **Deploy (frontend)** | Vercel | Free for personal projects | ❌ Not started |
| **Deploy (backend)** | Railway | $5 free credit/month | ❌ Not started |
| **Code** | GitHub (public repo) | Recruiters will see this | ❓ Unknown |

---

## Architecture

```
┌─────────────────────────────┐
│       Next.js Frontend      │  ← NOT BUILT YET
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ Upload   │ │ Pipeline │ │ Results     │  │
│  │ Page     │ │ View     │ │ Table       │  │
│  └──────────┘ └──────────┘ └─────────────┘  │
└──────────────┬──────────────┘
               │ REST API
┌──────────────▼──────────────┐
│       FastAPI Backend       │  ← DONE
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ Upload   │ │ Planner  │ │ Pipeline    │  │
│  │ Handler  │ │ Engine   │ │ Runner      │  │
│  └──────────┘ └──────────┘ └─────────────┘  │
│  ┌─────────────────────────────────────────┐  │
│  │           Agent Registry              │  │
│  │  OCR │ Extract │ Rules │ Format       │  │  ← ALL 5 REGISTERED
│  └─────────────────────────────────────────┘  │
└──────────────┬──────────────┘
               │
┌──────────────▼──────────────┐
│   Supabase (DB + Storage)   │  ← OPTIONAL (in-memory fallback)
└─────────────────────────────┘
```

---

## Pages (Frontend)

### 1. Landing Page (`/`)

- [ ] Hero: "Describe your task. Upload documents. AI does the rest."
- [ ] Upload zone (drag & drop)
- [ ] Text input for task description
- [ ] "Run Pipeline" button

### 2. Pipeline View (`/pipeline/:id`)

- [ ] Shows each agent step as a card
- [ ] Real-time status: queued -> running -> done / failed
- [ ] Expandable: click a step to see its input/output
- [ ] Progress bar

### 3. Results Page (`/results/:id`)

- [ ] Table view of extracted/processed data
- [ ] Download buttons: CSV, JSON
- [ ] Summary stats (documents processed, fields extracted, flags raised)

### 4. History Page (`/history`)

- [ ] List of past pipeline runs
- [ ] Click to revisit results

---

## API Endpoints (Backend)

### Original spec

| Method | Endpoint | What it does | Status |
|--------|----------|--------------|--------|
| POST | `/api/upload` | Upload documents, returns upload_id | ✅ |
| POST | `/api/pipeline/create` | Send task description + upload_id -> planner creates pipeline | ✅ |
| GET | `/api/pipeline/:id` | Get pipeline status + steps | ❌ *(plans are ephemeral; use runs API instead)* |
| GET | `/api/pipeline/:id/results` | Get final results | ❌ *(use `GET /api/runs/{id}` instead)* |
| GET | `/api/pipelines` | List past pipeline runs | ❌ *(use workflows/runs APIs instead)* |
| GET | `/api/health` | Health check | ✅ |

### Built beyond original spec

| Method | Endpoint | What it does | Status |
|--------|----------|--------------|--------|
| POST | `/api/users` | Create user | ✅ |
| GET | `/api/users/{id}/workflows` | List user's workflows | ✅ |
| POST | `/api/runs/adhoc` | Plan + run in one call | ✅ |
| POST | `/api/runs` | Run explicit steps | ✅ |
| GET | `/api/runs/{id}` | Get run results | ✅ |
| POST | `/api/workflows` | Save workflow template | ✅ |
| POST | `/api/workflows/from-run/{id}` | Save plan from a run | ✅ |
| GET | `/api/workflows/{id}/runs` | List all runs for a workflow | ✅ |
| POST | `/api/workflows/{id}/runs` | Rerun saved workflow | ✅ |
| POST | `/api/extract` | Debug: extract from raw text | ✅ *(debug only)* |

---

## Database Schema

> **Note:** Implemented schema differs from original spec. We use `users`, `workflows`, `workflow_steps`, `workflow_runs`, `workflow_step_runs`. See `backend/supabase/schema.sql`.

### pipelines *(original spec — not implemented as-is)*

| Column | Type |
|--------|------|
| id | UUID (PK) |
| task_description | TEXT |
| status | ENUM (planning, running, completed, failed) |
| steps | JSONB (array of step configs) |
| created_at | TIMESTAMP |
| completed_at | TIMESTAMP |

### pipeline_steps *(original spec — replaced by workflow_steps + workflow_step_runs)*

| Column | Type |
|--------|------|
| id | UUID (PK) |
| pipeline_id | UUID (FK) |
| step_order | INT |
| agent_type | VARCHAR |
| status | ENUM (queued, running, completed, failed) |
| input_data | JSONB |
| output_data | JSONB |
| started_at | TIMESTAMP |
| completed_at | TIMESTAMP |

### documents *(original spec — files on disk, metadata in upload response)*

| Column | Type |
|--------|------|
| id | UUID (PK) |
| pipeline_id | UUID (FK) |
| filename | VARCHAR |
| file_type | VARCHAR |
| storage_path | VARCHAR |
| extracted_text | TEXT |
| created_at | TIMESTAMP |

---

## Build Plan

### Week 1: Backend + Core Pipeline

**Day 1-2: Project setup + Upload**

- [x] Init FastAPI project with poetry/pip
- [x] `/api/upload` endpoint - accept PDF/image, save to local storage
- [x] PDF text extraction with PyMuPDF
- [x] OCR with Tesseract for images/scanned PDFs
- [x] Test with 3-4 sample documents

**Day 3-4: Planner + Agent framework**

- [x] Define base Agent class (input -> process -> output)
- [x] Build Planner agent (LLM call -> returns list of steps)
- [x] Build Field Extractor agent (LLM call -> structured JSON)
- [x] Build Rules agent (apply conditions to extracted data)
- [x] Build Formatter agent (compile results into CSV/JSON)

**Day 5: Pipeline runner**

- [x] Pipeline executor: runs agents in sequence
- [x] Status tracking per step
- [x] Store results in Supabase *(code done; optional — in-memory fallback works)*
- [x] End-to-end test: upload -> plan -> execute -> results

**Bonus (beyond Week 1 spec):**

- [x] Unified agent registry
- [x] Workflows (save + rerun without planner)
- [x] Users (`user_id` scopes workflows)
- [x] Run history per workflow + `document_ids` on runs
- [x] Manual API test guide (`backend/MANUAL_API_TEST.md`)

### Week 2: Frontend

**Day 1-2: Setup + Landing page**

- [ ] Init Next.js project with TypeScript + Tailwind + shadcn/ui
- [ ] Landing page: upload zone + task description input
- [ ] Connect to backend API

**Day 3-4: Pipeline + Results views**

- [ ] Pipeline view: show steps with status indicators
- [ ] Poll backend for status updates (or use SSE)
- [ ] Results table with data display
- [ ] CSV/JSON download buttons

**Day 5: History + Polish**

- [ ] History page: list past runs
- [ ] Error handling, loading states
- [ ] Mobile-responsive layout
- [ ] Clean README with screenshots

### Week 3: Deploy + Demo

**Day 1-2: Deployment**

- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Vercel
- [ ] Set up environment variables
- [ ] Supabase production setup
- [ ] End-to-end smoke test on live URLs

**Day 3: Demo + Portfolio**

- [ ] Record 60-sec demo video (screen recording)
- [ ] Write detailed README (problem, solution, architecture, screenshots, demo link)
- [ ] Add to LinkedIn profile
- [ ] Add to resume

---

## Cost

| Item | Monthly cost |
|------|--------------|
| OpenAI API (planner calls) | ~$3-5 *(using Groq = $0)* |
| Groq (extraction agents) | $0 (free tier) |
| Tesseract OCR | $0 (local) |
| Railway (backend) | $0-5 |
| Vercel (frontend) | $0 |
| Supabase (DB + storage) | $0 |
| **Total** | **~$3-10/month (~₹250-800)** *(currently ~$0 with Groq)* |

---

## What This Proves To Employers

1. **System design** - you designed a multi-agent pipeline architecture — ✅ backend done
2. **AI/LLM integration** - planner + extraction via API — ✅ done
3. **Python backend** - FastAPI, async, clean API design — ✅ done
4. **Frontend** - Next.js, TypeScript, modern UI — ❌ not started
5. **Full-stack deployment** - live, working, clickable demo — ❌ not started
6. **Document processing** - OCR, PDF parsing, structured extraction — ✅ done
7. **Database design** - normalized schema, JSONB for flexibility — ⚠️ schema written, Supabase optional

This is not a tutorial project. This is production-level architecture on a public repo.

---

*Created: 2026-08-02*  
*Updated: 2026-08-04*
