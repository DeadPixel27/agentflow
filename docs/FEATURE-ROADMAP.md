# AgentFlow — Feature Roadmap

*Standout features that differentiate AgentFlow. Ordered by impact vs effort.*

---

## Feature Roadmap Timeline

| Phase | Feature | When |
|---|---|---|
| **MVP (this week)** | Template Library | Before launch |
| **V1.1 (week after launch)** | Email delivery via Resend | First paid feature |
| **V1.2 (month 1)** | Google Sheets push | Pro tier differentiator |
| **V2.0 (month 2-3)** | Auto-correct learning | Moat builder |
| **V3.0 (month 4+)** | Watch folder / inbox automation | Premium tier |

---

## Feature 1: Template Library ⭐ BUILD FIRST

**What:** Pre-built pipelines - "Invoice Parser", "Resume Screener", "Contract Analyzer", "Receipt Scanner", "Purchase Order Extractor". User picks one, uploads docs, gets results. Zero typing needed.

**Why it matters:**
- Reduces friction to zero - new users get value in 30 seconds
- Great for demo video - show 5 templates working instantly
- Improves conversion - users don't have to figure out what to type

**How to build:**
- Create curated workflows with optimized task descriptions and configs
- Add a `/api/templates` endpoint that returns the list
- Frontend: template picker grid on landing page (icon + name + description)
- On click: pre-fill the task description OR skip it entirely and go straight to upload
- Store as seed data in Supabase or hardcoded JSON

**Effort:** Low - 2-3 hours. The workflow system already exists.

---

## Feature 2: Push to Google Sheets / Email ⭐ PAID TIER

**What:** After extraction, auto-push results to a Google Sheet or email as Excel/CSV attachment. Not just download – deliver to where users already work.

**Why it matters:**
- Turns AgentFlow from a tool into a **workflow**
- Creates habit and retention – users come back because it's plugged into their process
- Natural upsell: "Free = download only. Pro = push to Sheets/email"

**How to build:**
- Google Sheets: use `google-api-python-client` + OAuth2 consent flow
- Create sheet -> write headers -> append rows
- Email: use `resend` (free tier: 3000 emails/month, $0)
- Generate CSV attachment -> send via Resend API
- Add `output_destination` field to run request: `"download"` | `"google_sheets"` | `"email"`
- Frontend: dropdown in results page – "Send to Google Sheets" / "Email results"

**Effort:** Medium – 4-6 hours. Google OAuth is the tricky part.

---

## Feature 3: Auto-Correct Learning 🧠 MOAT BUILDER

**What:** When extraction is wrong, user clicks a field, corrects it. System stores the correction. Next time the same doc type comes in, accuracy improves automatically.

**Why it matters:**
- **This is what makes Nanonets sticky** — the product gets better the more you use it
- Hard to copy — requires feedback loop + prompt engineering + user data
- Becomes more valuable over time — real defensibility

**How to build:**
- Add a "Correct this field" button next to each extracted value in the results view
- Store corrections in a `corrections` table: `{doc_type, field_name, wrong_value, correct_value, context}`
- On next extraction of same doc type, inject past corrections into the LLM prompt as few-shot examples:
```
---
Previous corrections for this document type:
- "vendor" was extracted as "ACME" but should be "Acme Corporation"
- "date" format should be YYYY-MM-DD, not DD/MM/YYYY
---
```
- Track accuracy improvement over time per user

**Effort:** High — 8-12 hours. Needs feedback UI + prompt engineering + correction storage.

---

## Feature 4: Watch Folder / Email Inbox 📁 AUTOMATION

**What:** Connect a Google Drive folder or email inbox. New documents are auto-processed when they arrive. Results delivered to Sheets/email without lifting a finger.

**Why it matters:**
- Set-and-forget automation — users never have to open the app
- Highest retention feature — once connected, users never leave
- Premium tier feature — worth $50-100/mo alone

**How to build:**
- Google Drive: use Drive API watch/push notifications or poll every 5 min
- Email: use Gmail API with pub/sub or IMAP polling
- Background worker: Celery or APScheduler for periodic checks
- On new file detected → run saved workflow → push results to configured destination
- Frontend: "Connect Google Drive" / "Connect Gmail" buttons in settings

**Effort:** High — 12-20 hours. Needs background workers + OAuth + webhook handling.

---

## Standout UI Feature: Live Document Preview with Extraction Highlights

**What:** Split-screen view — original document on the left, extracted fields on the right with highlighted source text showing WHERE each value came from.

**Why it matters:**
- Builds trust — user can verify accuracy visually
- Nanonets has this, budget tools don't — puts you in premium tier
- Looks incredible in demo videos — screenshot-worthy for Product Hunt

**How to build:**
- Use `react-pdf` to render PDF pages in browser
- Field extractor agent returns character offsets alongside extracted values
- Overlay highlight boxes on the rendered PDF at those positions
- Click a highlight -> jumps to the corresponding field in the results panel
- Coordinate mapping: OCR engine provides bounding boxes, draw SVG overlays on top.

**Effort:** Medium-High - 6-10 hours. PDF rendering + coordinate mapping.

---

*Transcribed from screenshots.*
