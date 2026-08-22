# Nexora — Scaling, Jobs & Future Ops

**Updated:** 2026-08-16  
**Audience:** when you outgrow a single Railway API process + in-process `BackgroundTasks`.

This doc captures decisions from the launch hardening review so we do **not** reopen them casually during ship week. For near-term product tasks see [NEXT-STEPS.md](./NEXT-STEPS.md).

**Rule:** Whenever we defer a scaling, reliability, cost, extraction-architecture, or ops change, **add it here in the same PR/change** (see `.cursor/rules/scaling-and-jobs.mdc`). Do not leave “we’ll do it later” only in chat.

---

## Mental model (keep this)

When a user starts an extraction today:

1. API writes a run row with `status=running` (sticky note on the wall).
2. FastAPI `BackgroundTasks` runs `execute_run` **inside the same process** (intern at your desk).

If the process dies (redeploy, crash, restart), the intern is gone but the sticky note still says “in progress.” That is an **orphan run**. Launch fix: **reclaim** (mark failed + refund pages + stop endless UI polling). Long-term fix: a **job queue** so work survives API restarts.

---

## Launch posture (now)

| Choice | Why |
|--------|-----|
| **One Railway API replica** | BackgroundTasks are in-process; multi-replica + “fail all running on startup” can kill live jobs on another box |
| **No Redis / no worker service yet** | Avoid extra monthly cost until load or multi-replica needs it |
| **Orphan reclaim** | Users are not stuck forever; pages refunded; job is **not** auto-retried (user can re-run) |
| **No extraction parallelism yet** | Batch LLM call is simpler/cheaper; parallel OCR/LLM adds cost and failure complexity |
| **Max 10 pages per file** | Single GPT-4o call over full joined text; hard reject over-limit PDFs (UI warns). Raise when chunked extract ships (`MAX_PAGES_PER_FILE`) |
| **OpenAI spend brakes** | Global daily pages + estimated `OPENAI_DAILY_BUDGET_USD` (in-process) while credit balance is small |

Rough capacity on this posture: a handful of concurrent heavy runs, product caps (pages/day, rate limits) usually bite before the box does. Fine for early launch traffic; not for “hundreds extracting at once.”

---

## Later: job queue (when Redis is OK)

### What to add

1. **Redis** (Railway Redis, Upstash, etc.) — shared to-do list.
2. **Worker service** — separate process that only pulls jobs and calls `execute_run`.
3. **API change** — after `start_run`, **enqueue `run_id`** instead of `BackgroundTasks.add_task`.
4. Keep **stale reclaim** as a safety net (running longer than N minutes → fail + refund).

Libraries that fit this stack well: **Arq** (async + Redis) or **RQ**. Celery works but is heavier for this app size.

### Cost (order of magnitude)

- Queue libraries: free/open source.
- Money: **Redis instance + second Railway service (worker)**.
- Do this when you need restart-safe jobs or multiple API replicas — not required for first launch.

### Multi-replica / multi-server

```
User → API replica A or B or N
         │
         ├─► Postgres (run status)
         └─► Redis queue (run_id)
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
      Worker 1              Worker 2
         │                     │
         └──────► GPT / OCR ───┘
                      │
                      ▼
                   Postgres
```

- **APIs** scale for HTTP (uploads, poll, auth). They do not do heavy extract work in-process.
- **Workers** scale for OCR/LLM load independently.
- Restarting APIs does **not** drop queued or in-flight worker jobs (workers own that).
- Worker crash: queue retries / another worker picks up (design idempotency carefully).

**Do not** turn on multi-replica API autoscaling while jobs still use `BackgroundTasks`.

---

## Later: long-document / chunked extraction

**Current behavior (launch):**

- PDF text: page-by-page extract → **join into one string**.
- Field extract: **one** GPT-4o call with the full document text (whole upload batch in one prompt).
- Metering: bill by PDF page count; LLM sees one concatenated blob.
- Guardrail: **`MAX_PAGES_PER_FILE=10`** — reject over-limit files (HTTP upload + inbound). Frontend shows the limit and rejects when page count is detectable.

**When to change (measured pain):**

| Symptom | Direction |
|---------|-----------|
| Missed mid-doc fields / truncated line items on 8–10 page tables | Chunk by page or section |
| Context / token errors on dense PDFs | Chunk + merge |
| Latency on multi-file batches | Parallel OCR first; then capped parallel LLM |
| Users need 20–50 page contracts | Raise page cap **only after** chunked extract ships |

**Preferred chunk design (when we build it):**

1. Split text by page (or ~N pages / ~token budget) with overlap for headers.
2. Parallel GPT-4o calls **with a hard concurrency cap** (not unbounded `gather`).
3. Reconcile: header fields from page 1 / highest-confidence; **merge arrays** (line items) and dedupe.
4. Metering stays page-based; log OpenAI `$` per chunk via existing usage estimate.
5. Then raise `MAX_PAGES_PER_FILE` (e.g. 25–50) and update UI copy.

Do **not** ship unbounded parallel LLM for launch. Do **not** remove the per-file page cap until reconcile exists.

---

## Later: extraction parallelism (only if measured)

Current behavior:

- Field extract: **one** GPT-4o call for the whole document batch.
- OCR / text extract: documents **sequentially** in the handler.
- Pipeline steps: sequential (by design).

Prefer, in order, when multi-file uploads feel slow:

1. Measure (OCR vs LLM vs network).
2. **Chunked batches** (e.g. N docs per LLM call) if context/size hurts — see long-document section above.
3. Parallel OCR across docs if OCR is the bottleneck (watch CPU on one box).
4. Parallel per-doc LLM only with clear caps — more $$, rate limits, partial failure, metering races.

Do **not** add unbounded `asyncio.gather` over LLM calls for launch.

---

## Later: cost & metering ops

| Item | Notes |
|------|--------|
| Persist OpenAI spend beyond one API process | Today `openai_cost` day totals are **in-process**; multi-replica needs Redis/DB |
| Admin `/api/admin/openai-spend` | Snapshot only for the replica that handled calls |
| Route simple templates to `gpt-4o-mini` | Big $/page win once quality is validated |
| Upload TTL cleanup sweep | **Not for launch.** Implement later as **RetentionCleanupService** (separate from OwnerRefineService). Policy: delete upload bytes + `cached_documents` + `result` cells; keep refinement events + prompt blobs + catalog so master refine still works without PDFs. Product copy: [NEXT-STEPS.md](./NEXT-STEPS.md). |
| Structured logs + `audit_events` | **Shipped in-process.** Stdout includes `rid`/`uid`. `audit_events` is append-only activity (no payloads). Central log drain (Datadog/Axiom) still later. |
| Per-transaction rules (e.g. flag debits > X in `transactions[]`) | **Deferred.** `transform.rules` compares scalar fields only; bank `large_transaction` rule removed at launch (was broken on array field). **Trigger:** users want approval flags on individual statement lines. **Approach:** extend rules agent or post-process in refine. |

---

## Related hardening still on the senior-review list

Track these separately from product NEXT-STEPS; some may already be done in-branch:

| # | Topic | Notes |
|---|--------|--------|
| 4 | Orphan-run reclaim | Launch; no Redis |
| 5 | Metering harden | Fail closed on `record_usage`; reduce check-then-act races |
| 6 | Upload ownership (IDOR) | Bind uploads to `user_id` |
| 7 | Supabase RLS / private buckets | Defense in depth beyond service role |
| 8 | Inbound webhook replay window | Timestamp skew on Mailgun HMAC |
| 9 | Broader rate limits | runs/workflows/extract/plan/waitlist |
| 10 | Reject memory persistence in prod | Health fail if `persistence=memory` in production |

Already addressed in recent hardening: refine page metering (#1), email/Sheets caps (#2), document capability tokens instead of JWT-in-query (#3).

---

## Triggers: when to leave “launch posture”

Add Redis + workers when any of these become true:

- You want **more than one** API replica / autoscaling.
- Redeploys are frequent and **re-running failed orphan jobs** is painful for users.
- Concurrent extracts saturate the single process (queue backs up in practice).
- You need retries, delayed jobs, or priority queues.

Raise per-file page limits / add chunked extract when:

- Real users hit the **10-page** reject often with valid use cases.
- Accuracy on dense multi-page tables is measurably bad under single-call extract.

Until then: one replica, BackgroundTasks, orphan reclaim, product caps, 10 pages/file.
