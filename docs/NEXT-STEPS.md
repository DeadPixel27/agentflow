# AgentFlow — Next Steps

**Updated:** 2026-08-10  
**Branch:** `develop`

Launch product through V3 + launch features is built. Recent ship: side-by-side run results, run history UX, email/sheets outbound testing, unsigned-home auth fix, shared user session for nav badge, realistic sample invoice.

---

## Done recently

- [x] PDF / document side-by-side on run page (All results + per-doc view)
- [x] Vertical / horizontal results layout toggle (per-doc)
- [x] Refine UX: Apply clearly re-runs **all documents** in the run
- [x] Batch CSV export (already covered by full `result.rows` + Export bar)
- [x] Run history: filenames, timestamps, doc counts, status/search filters; original filename persistence
- [x] Email + Sheets outbound testing
- [x] Fix unsigned home + auth UX (public templates catalog; 401 redirect only with token; Back to home on `/account`)
- [x] Fix nav badge after login (`UserProvider` shared session)
- [x] Replace sample invoice PDF (frontend + backend samples)

---

## Next (recommended order)

| # | Task | Est. | Notes |
|---|------|------|-------|
| 1 | **Deploy** | ~4h | Supabase + Railway (backend) + Vercel (frontend) + domain + smoke test. |
| 2 | **Real-doc testing** | ~3h | 3–5 docs each: invoice, receipt, resume. Score accuracy **before** any hardening. |
| 3 | **Launch kit** | ~2h | 60s Loom + Reddit / IH / HN drafts + README with screenshots + live URL. |

---

## Deferred

- SEO template pages (`/templates/[slug]`) — hold for now
- Rebrand from AgentFlow — hold for now
- Inbound email IMAP poll (unread + attachments every 15 min → one batched run → mark read) — hold for later

---

## Hold until after launch

- Adhoc field-name locking (optional chips → fixed `json_schema`) — English planner already shares one field list per run; skip for launch
- Targeted extraction hardening (only if real-doc tests fail)
- Editable cells + corrections
- Run diff / validation suggestions
- Stripe, self-learning, rule engine, dynamic schema via chat

**Research locks (do not reopen for launch):** stay on GPT-4o, keep RapidOCR, per-page metering, no blind prompt hardening, no Claude routing yet.

---

## Immediate next action

Start **#1 Deploy**.
