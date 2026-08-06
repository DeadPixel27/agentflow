# AgentFlow — Plan & Next Steps

**Status (2026-08-06):** MVP complete. Pre-deploy hardening on `feature/pre-deploy-gaps` (most Phase 1–2 items done). **All screenshot docs transcribed.** Track open items in [SPEC.md § Master Tracker](./SPEC.md#master-tracker).

This file is the actionable sprint plan. Estimated **~7–9 hours** to production-ready, then feature work.

---

## Phase 0 — Done ✅

- [x] Backend: 5 agents, planner, async runner, Supabase persistence
- [x] Persistence + auth registry pattern (Protocol → implementation → registry)
- [x] FastAPI `Depends()` service injection
- [x] Frontend: upload, poll, results, workflows, account, email sign-in
- [x] E2E tested (upload → run → save workflow → sign out/in)
- [x] 19 backend tests passing
- [x] Docs organized in `docs/`

---

## Phase 1 — Deploy blockers (do first, ~1 hour)

| # | Task | Time | File / area | Status |
|---|------|------|-------------|--------|
| 1 | **CORS from env var** — not hardcoded `localhost:3000` | 10 min | `app/main.py`, `config.py` | ✅ |
| 2 | **Dockerfile** for backend (tesseract + poppler) | 15 min | `backend/Dockerfile` | ✅ |
| 3 | **Deploy backend** (Railway) + env vars | 30 min | Railway dashboard | ⬜ |
| 4 | **Deploy frontend** (Vercel) + `NEXT_PUBLIC_API_URL` | 20 min | Vercel dashboard | ⬜ |
| 5 | **Smoke test** on live URLs | 15 min | Manual | ⬜ |

**Exit criteria:** Live demo URL works end-to-end.

---

## Phase 2 — Security & reliability (~2 hours)

| # | Task | Time | Impact | Status |
|---|------|------|--------|--------|
| 6 | **Rate limiting** on `/api/runs/adhoc` (`slowapi`, 10/min) | 30 min | Cost protection | ✅ |
| 7 | **Prompt injection guard** — sanitize `task_description` before LLM | 30 min | Security | ✅ |
| 8 | **LLM retry** with `tenacity` (429, 503) in `groq_client.py` | 20 min | Reliability | ✅ |
| 9 | **File MIME validation** (`filetype`, not extension-only) | 30 min | Security | ✅ |
| 10 | **Error boundary** in `frontend/src/app/error.tsx` | 15 min | UX | ✅ |

See [GAPS-TECHNICAL.md](./GAPS-TECHNICAL.md) for exact implementation notes.

---

## Phase 3 — Code quality & ops (~2 hours)

| # | Task | Time | Status |
|---|------|------|--------|
| 11 | Deduplicate `_to_planned_steps()` → shared util | 10 min | ✅ |
| 12 | Upload file cleanup (24h TTL sweep) | 1–2 hr | ⬜ |
| 13 | GitHub Actions CI (`pytest` + `npm run build`) | 30 min | ⬜ |
| 14 | Root README: screenshots + live demo link | 30 min | ⬜ |
| 15 | 60-sec demo video | 30 min | ⬜ |

---

## Phase 4 — Auth upgrade (before public launch, ~4 hours)

| # | Task | Time | Notes |
|---|------|------|-------|
| 16 | **Supabase Auth** provider (`services/auth/supabase_provider.py`) | 3–4 hr | Replace email-only; registry already ready |

Email lookup auth is fine for demo; real passwords/magic links needed for strangers on the internet.

---

## Phase 5 — First product feature (post-launch, ~3 hours)

**Build first:** [Template Library](./FEATURE-ROADMAP.md#feature-1-template-library-build-first)

1. ✅ Seed 7 templates (invoice, resume, receipt, … — see [TEMPLATES.md](./TEMPLATES.md))
2. ✅ `GET /api/templates` endpoint
3. ✅ Frontend template picker grid on landing page
4. ✅ Selecting a template pre-fills task description
5. ✅ Rich templates: `extraction_instructions`, `POST /api/runs/template` (screenshot spec)
6. ⬜ Run `backend/supabase/setup_templates.sql` if Supabase configured (upgrades table + syncs seeds)

---

## Phase 6 — Differentiators (V1.1+)

| Version | Feature | Effort | Doc |
|---------|---------|--------|-----|
| V1.1 | Email delivery (Resend) | Medium | FEATURE-ROADMAP |
| V1.2 | Google Sheets push | Medium | FEATURE-ROADMAP |
| V1.3 | Chat refinement on results | High | CHAT-REFINEMENT |
| V2.0 | Live PDF preview + field highlights | 6–10 hr | FEATURE-ROADMAP |
| V3.0 | Watch folder / inbox automation | 12–20 hr | FEATURE-ROADMAP |

---

## Git workflow (reminder)

```
feature/deploy-cors-docker  →  develop  →  main (release)
```

Never commit directly to `main`. One feature branch per task.

---

## What NOT to do now

- Don't add `dependency-injector` — FastAPI `Depends()` is enough
- Don't refactor runner to use `Depends()` — background tasks can't
- Don't build SSE until deploy works — polling is fine
- Don't add S3 until you need it — registry is ready

---

*Updated: 2026-08-06 — Phase 1–2 items marked done on branch; docs transcription complete*
