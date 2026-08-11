# AgentFlow — Scaling, Jobs & Future Ops

**Updated:** 2026-08-11  
**Audience:** when you outgrow a single Railway API process + in-process `BackgroundTasks`.

This doc captures decisions from the launch hardening review so we do **not** reopen them casually during ship week. For near-term product tasks see [NEXT-STEPS.md](./NEXT-STEPS.md).

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

## Later: extraction parallelism (only if measured)

Current behavior:

- Field extract: **one** GPT-4o call for the whole document batch.
- OCR / text extract: documents **sequentially** in the handler.
- Pipeline steps: sequential (by design).

Prefer, in order, when multi-file uploads feel slow:

1. Measure (OCR vs LLM vs network).
2. **Chunked batches** (e.g. N docs per LLM call) if context/size hurts.
3. Parallel OCR across docs if OCR is the bottleneck (watch CPU on one box).
4. Parallel per-doc LLM only with clear caps — more $$, rate limits, partial failure, metering races.

Do **not** add unbounded `asyncio.gather` over LLM calls for launch.

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
- Concurrent extractions saturate the single process (queue backs up in practice).
- You need retries, delayed jobs, or priority queues.

Until then: one replica, BackgroundTasks, orphan reclaim, product caps.
