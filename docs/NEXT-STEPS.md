# Nexora — Next Steps

**Updated:** 2026-08-11  
**Branch:** `develop`

Launch product (V2/V3 + auth/metering) is built. Remaining work below.

---

## This week (ship)

| # | Task | Est. | Notes |
|---|------|------|-------|
| 1 | **Hard usage caps per feature** | ~3–4h | Hard caps (not soft warnings) for extract/pages, refine, emails, Sheets; clear 429 UI. Refine: reject out-of-scope prompts before LLM spend. |
| 2 | **Deploy** | ~4h | Supabase + Railway + Vercel + domain + smoke test. See [DEPLOYMENT.md](./DEPLOYMENT.md). |
| 3 | **Real-doc testing** | ~3h | 3–5 docs each: invoice, receipt, resume. Score accuracy before extra hardening. |
| 4 | **Launch kit** | ~2h | 60s Loom + Reddit / IH / HN drafts + README screenshots + live URL. |

---

## Deferred (post-launch)

- SEO template pages (`/templates/[slug]`)
- Inbound email IMAP poll (unread + attachments → batched run)
- Job queue / Redis / multi-replica — [SCALING-AND-JOBS.md](./SCALING-AND-JOBS.md)
- GitHub Actions CI (`pytest` + `npm run build`)
- Upload TTL cleanup sweep
- Frontend tests (Vitest)
- Supabase Auth (password / magic link) — JWT+Google is enough for launch

---

## Later product ideas

| Idea | Notes |
|------|-------|
| Live PDF preview + field highlights | Split view; highlight source spans |
| Auto-correct / learning from edits | Store corrections → few-shot on next similar docs |
| Editable cells + run diff / validation suggestions | Results UX polish |
| Watch folder / inbox automation | Drive/Gmail → saved workflow → Sheets/email |
| New agents | Summarizer, classifier, table extract — [AGENTS.md](./AGENTS.md) |
| Stripe, rule engine, dynamic schema via chat | Monetization / power features |

**Research locks (do not reopen for launch):** GPT-4o extract, RapidOCR, per-page metering, no blind prompt hardening, no Claude routing yet.

---

## Immediate next action

Start **#1 Hard usage caps**, then **#2 Deploy**.
