# Frontend guide (Next.js)

Quick map of the `frontend/` folder for AgentFlow.

## How Next.js routing works

Each folder under `src/app/` becomes a **URL route**:

```
src/app/page.tsx                    →  /
src/app/account/page.tsx            →  /account
src/app/workflows/page.tsx          →  /workflows
src/app/workflows/[workflowId]/page.tsx  →  /workflows/abc-123
src/app/results/[runId]/page.tsx    →  /results/xyz-456
```

`[workflowId]` and `[runId]` are **dynamic segments** — the value comes from the URL.

## Directory structure

```
frontend/
├── src/
│   ├── app/                 # Pages (routes) + global layout
│   │   ├── layout.tsx       # Wraps every page (fonts, CSS)
│   │   ├── page.tsx         # Home — upload + run adhoc
│   │   ├── globals.css      # Tailwind + theme colors
│   │   ├── account/         # Create / view user
│   │   ├── workflows/       # List + detail + rerun
│   │   └── results/         # Run results
│   │
│   ├── components/          # Reusable UI pieces
│   │   ├── ui/              # shadcn primitives (Button, Card, …)
│   │   ├── app-header.tsx   # Top nav
│   │   ├── upload-zone.tsx  # Drag-and-drop files
│   │   ├── rerun-panel.tsx  # Upload + rerun saved workflow
│   │   ├── workflow-run-list.tsx  # Table of runs for a workflow
│   │   └── run-display.tsx  # Step list + results table
│   │
│   ├── hooks/               # React hooks (e.g. useUser)
│   └── lib/                 # Non-UI logic
│       ├── api.ts           # All backend HTTP calls
│       ├── user-session.ts  # localStorage user id/name
│       └── utils.ts         # className helper (cn)
│
├── .env.local               # NEXT_PUBLIC_API_URL (not committed)
├── package.json
└── tailwind.config.ts
```

## Key concepts

| Term | Meaning |
|------|---------|
| **Server Component** | Default in App Router — runs on server, no `useState` |
| **Client Component** | `"use client"` at top — interactivity, hooks, browser APIs |
| **`lib/api.ts`** | Single place that talks to FastAPI (`localhost:8000`) |
| **`user-session.ts`** | Stores `user_id` in `localStorage` (no auth yet) |
| **shadcn/ui** | Copy-paste components in `components/ui/` |

## Data flow (example: Run pipeline)

```
page.tsx (user clicks Run)
  → uploadFiles()        POST /api/upload
  → runAdhoc()           POST /api/runs/adhoc
  → router.push(`/results/${run_id}`)
  → results page calls getRun()
```

## Data flow (rerun saved workflow)

```
workflows/[id]/page.tsx
  → uploadFiles()
  → runWorkflow(id, upload_id)   POST /api/workflows/{id}/runs
  → redirect to /results/{run_id}
```

## Run locally

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Backend must be on http://localhost:8000.
