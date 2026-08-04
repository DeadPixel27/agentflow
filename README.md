# AgentFlow

Describe what you want done with your documents → AI builds and runs a multi-agent pipeline automatically.

Upload PDFs or images, describe the task in plain English, and get structured JSON/CSV output. Save successful runs as reusable workflows and rerun on new files without re-planning.

## What it does

1. **Upload** documents (PDF, PNG, JPG)
2. **Describe** the task (e.g. *"Extract vendor, amount, date. Flag over ₹50K. CSV."*)
3. **Planner** (Groq LLM) builds a step-by-step pipeline
4. **Runner** executes agents in sequence
5. **Save** the plan as a workflow and **rerun** on new uploads

## Agent types

| Stage | Agent | `agent_type` |
|-------|--------|----------------|
| Process | Text Extractor | `processor.text_extract` |
| Process | OCR (Tesseract) | `processor.ocr` |
| Transform | Field Extractor (LLM) | `transform.field_extractor` |
| Transform | Rules (flags/filters) | `transform.rules` |
| Output | Formatter (CSV/JSON) | `output.formatter` |

## Tech stack

- **Backend:** Python 3.9+, FastAPI, Groq (Llama 3.3)
- **PDF/OCR:** PyMuPDF, Tesseract
- **Persistence:** Supabase (optional) or in-memory
- **Frontend:** Next.js (planned)

## Quick start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add GROQ_API_KEY
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

### Run tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

### Manual API walkthrough

See [backend/MANUAL_API_TEST.md](backend/MANUAL_API_TEST.md).

## Main API flow

```
POST /api/users
POST /api/upload
POST /api/runs/adhoc              # plan + run
POST /api/workflows/from-run/{id}  # save workflow
POST /api/workflows/{id}/runs     # rerun without planner
GET  /api/workflows/{id}/runs     # run history
```

## Project structure

```
backend/
├── app/
│   ├── api/routes/       # HTTP endpoints
│   ├── agents/           # Agent registry + handlers
│   ├── models/           # API + domain models
│   ├── persistence/      # Supabase / in-memory store
│   └── services/         # Planner, runner, upload, LLM
├── supabase/             # DB schema + migrations
├── tests/
└── samples/              # test_invoice.pdf
SPEC.md                   # Full product spec + progress
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | Yes | Groq API key for planner + extraction |
| `SUPABASE_URL` | No | Postgres persistence |
| `SUPABASE_SECRET_KEY` | No | Supabase service role key |

## Contributing / Git workflow

We use a simple **Git Flow**-style setup:

| Branch | Purpose |
|--------|---------|
| `main` | Stable, deployable code (releases) |
| `develop` | Integration branch — day-to-day work merges here |
| `feature/*` | One branch per task (e.g. `feature/supabase-setup`) |

### Day-to-day

```bash
git checkout develop
git pull origin develop
git checkout -b feature/my-task

# ... make changes, commit ...

git push -u origin feature/my-task
# Open a PR: feature/my-task → develop
```

### Release to production

When `develop` is tested and ready:

```bash
# Open a PR: develop → main
# Or locally:
git checkout main
git merge develop
git push origin main
```

**Rule of thumb:** never commit directly to `main` — always go through `develop` or a feature branch.

## License

MIT (or your choice — update before publishing)
