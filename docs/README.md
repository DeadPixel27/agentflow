# AgentFlow — Documentation Index

All project documentation, split by topic. Updated Aug 5, 2026.

> **For AI assistants:** Read [ENGINEERING-PRINCIPLES.md](./ENGINEERING-PRINCIPLES.md) before writing code. Use [GAPS-TECHNICAL.md](./GAPS-TECHNICAL.md) for pre-deploy checklist. Use [PLAN-AND-NEXT-STEPS.md](./PLAN-AND-NEXT-STEPS.md) for sprint order.

---

## Project Docs

| File | What's in it | When to use |
|------|--------------|-------------|
| [SPEC.md](./SPEC.md) | Product spec, MVP scope, tech stack, API endpoints, DB schema | Starting a new feature |
| [MARKET-ANALYSIS.md](./MARKET-ANALYSIS.md) | TAM, competitors, pricing, GTM plan | Positioning, pricing decisions |
| [ENGINEERING-PRINCIPLES.md](./ENGINEERING-PRINCIPLES.md) | 14 non-negotiable code rules with examples | **Before writing any code** |
| [PROMPTS.md](./PROMPTS.md) | All LLM system prompts, injection wrapper, template task text | Tuning extraction / planner / refine |
| [PLAN-AND-NEXT-STEPS.md](./PLAN-AND-NEXT-STEPS.md) | Ordered action plan (~7–9 hrs to prod-ready) | **Start here after MVP** |

---

## Gaps & Improvements

| File | What's in it | When to use |
|------|--------------|-------------|
| [GAPS-TECHNICAL.md](./GAPS-TECHNICAL.md) | 15 technical gaps with exact fixes + priority table | Sprint planning, pre-deploy checklist |
| [FEATURE-ROADMAP.md](./FEATURE-ROADMAP.md) | 4 standout features + timeline (MVP → V3.0) | Product planning, what to build next |

---

## Feature Designs

| File | What's in it | When to use |
|------|--------------|-------------|
| [TEMPLATES.md](./TEMPLATES.md) | 7 pipeline templates with prompts, fields, rules | Building the template library |
| [CHAT-REFINEMENT.md](./CHAT-REFINEMENT.md) | Chat refine flow, API design, data model, UI wireframe | Building the refine feature |
| [AGENTS.md](./AGENTS.md) | Current 5 agents + 9 planned + how to add new ones | Adding new agent types |

---

## Quick Links

| I want to… | Read |
|------------|------|
| Fix bugs / security | [GAPS-TECHNICAL.md](./GAPS-TECHNICAL.md) |
| What to build next | [FEATURE-ROADMAP.md](./FEATURE-ROADMAP.md) |
| How to write code | [ENGINEERING-PRINCIPLES.md](./ENGINEERING-PRINCIPLES.md) |
| Adding a template | [TEMPLATES.md](./TEMPLATES.md) |
| Adding an agent | [AGENTS.md](./AGENTS.md) |
| Tune LLM prompts | [PROMPTS.md](./PROMPTS.md) |
| Sprint order / deploy plan | [PLAN-AND-NEXT-STEPS.md](./PLAN-AND-NEXT-STEPS.md) |

---

## Code-adjacent docs (in repo)

| Path | Topic |
|------|--------|
| `backend/DOCUMENT_STORAGE.md` | Persistence registry, document backends |
| `backend/SUPABASE_SETUP.md` | Supabase Postgres + Storage setup |
| `backend/MANUAL_API_TEST.md` | API walkthrough |
| `frontend/FRONTEND.md` | Next.js directory guide |

---

## Source screenshots (archive)

Original WhatsApp screenshots (Opus 4.6 analysis) are archived under `docs/_archive/source-screenshots/`. **Do not edit the JPEG folders** — content has been transcribed into canonical markdown here.

| Folder | Transcribed to |
|--------|----------------|
| `engineering-patterns/` | [ENGINEERING-PRINCIPLES.md](./ENGINEERING-PRINCIPLES.md) |
| `technical-gaps-opus-4.6/` | [GAPS-TECHNICAL.md](./GAPS-TECHNICAL.md), [FEATURE-ROADMAP.md](./FEATURE-ROADMAP.md), [TEMPLATES.md](./TEMPLATES.md), [AGENTS.md](./AGENTS.md), [CHAT-REFINEMENT.md](./CHAT-REFINEMENT.md), [PROMPTS.md](./PROMPTS.md), [README.md](./README.md) |

For AI assistants and contributors: always follow [ENGINEERING-PRINCIPLES.md](./ENGINEERING-PRINCIPLES.md), not the JPEGs.
