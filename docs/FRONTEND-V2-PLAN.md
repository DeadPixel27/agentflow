# Frontend V2 — One-Shot Build Prompt for Cursor

> Transcribed from frontend-v2-opus4.6/ screenshots (Aug 8, 2026). Source images gitignored.

> **What this is:** A single, self-contained prompt you can paste into Cursor to rebuild the entire AgentFlow frontend to match the V2 design. It includes the complete design spec, every component, every CSS variable, every page layout, and the exact code for new files.
>
> **How to use:** Copy everything from `--- START PROMPT ---` to `--- END PROMPT ---` and paste it into Cursor as a single message. Cursor will have all the context it needs.

---

## --- START PROMPT ---

You are rebuilding the AgentFlow frontend to match a new V2 design. The codebase is at `github.com/kabirrao2002/agentflow` on the `develop` branch. You are working in `frontend/`.

### Stack

- Next.js 14.2.35 (App Router)
- TypeScript
- Tailwind CSS 3.4
- shadcn/ui components (already installed: badge, button, card, input, label, progress, table, textarea)
- Lucide React icons
- Sonner for toasts
- No additional dependencies needed

### What exists today (files you're modifying)

The current frontend has these pages:

- `/` -> `src/app/page.tsx` — verbose home with hero, "how it works" cards, template picker, upload zone, task textarea
- `/results/[runId]` -> `src/app/results/[runId]/page.tsx` — stacked cards layout (steps -> stats -> table -> versions -> chat -> save)
- `/workflows` -> `src/app/workflows/page.tsx` — 2-column card grid
- `/workflows/[workflowId]` -> `src/app/workflows/[workflowId]/page.tsx` — stacked (version panel, rerun+steps, run history)
- `/account` -> `src/app/account/page.tsx` — simple sign-in/sign-out form

Key existing components:

- `src/components/app-header.tsx` — nav bar with Home, Workflows, Account tabs + user name
- `src/components/upload-zone.tsx` — drag & drop file upload
- `src/components/refine-chat.tsx` — chat panel for refinement (Card-based)
- `src/components/rerun-panel.tsx` — upload zone for workflow reruns (Card-based)
- `src/components/run-display.tsx` — ResultsTable, RunSummaryStats, StepStatusList
- `src/components/template-picker.tsx` — template selection grid (Card-based, 2-column)
- `src/components/template-version-panel.tsx` — version history + revert (DELETE this file)
- `src/components/workflow-run-list.tsx` — run history table
- `src/components/empty-state.tsx` — empty state component

Existing lib:

- `src/lib/api.ts` — full API client
- `src/lib/user-session.ts` — localStorage session
- `src/lib/utils.ts` — cn() helper
- `src/lib/toast.ts` — toastError/toastSuccess
- `src/lib/upload-limits.ts` — file size/count limits

Existing hooks:

- `src/hooks/use-user.ts` — user session hook
- `src/hooks/use-run-polling.ts` — polling hook for run status

### Design system — CSS variables

Replace the current `globals.css` with this. The V2 design uses a warm stone palette with teal primary:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    /* V2 warm stone palette */
    --background: 40 33% 98%;      /* #FAF9F7 */
    --foreground: 24 10% 10%;      /* #1C1917 */
    --card: 0 0% 100%;             /* #FFFFFF */
    --card-foreground: 24 10% 10%;
    --popover: 0 0% 100%;
    --popover-foreground: 24 10% 10%;
    --primary: 175 83% 29%;        /* #0D9488 teal */
    --primary-foreground: 0 0% 100%;
    --secondary: 30 11% 96%;       /* #F3F1ED */
    --secondary-foreground: 24 10% 10%;
    --muted: 30 11% 96%;
    --muted-foreground: 25 6% 45%;  /* #78716C */
    --accent: 30 11% 96%;
    --accent-foreground: 24 10% 10%;
    --destructive: 0 72% 51%;      /* #DC2626 */
    --destructive-foreground: 0 0% 100%;
    --border: 30 7% 90%;           /* #E7E5E4 */
    --input: 30 7% 90%;
    --ring: 175 83% 29%;
    --radius: 0.625rem;

    /* Extended palette for V2 */
    --surface: 0 0% 100%;
    --surface-hover: 30 15% 94%;        /* #F3F1ED */
    --surface-2: 30 11% 93%;            /* #F0EEEA */
    --fg-soft: 24 8% 15%;               /* #292524 */
    --muted-2: 25 5% 64%;               /* #A8A29E */
    --border-s: 25 6% 83%;              /* #D6D3D1 */
    --primary-hover: 175 80% 24%;       /* #0F766E */
    --primary-soft: 166 76% 90%;        /* #CCFBF1 */
    --primary-softer: 166 76% 97%;      /* #F0FDFA */
    --success: 142 72% 29%;             /* #16A34A */
    --success-soft: 138 76% 93%;        /* #DCFCE7 */
    --warning: 32 95% 29%;              /* #B45309 */
    --warning-soft: 48 96% 89%;         /* #FEF3C7 */
    --blue: 217 91% 60%;                /* #2563EB */
    --blue-soft: 214 95% 93%;           /* #DBEAFE */
    --purple: 262 83% 58%;              /* #7C3AED */
    --purple-soft: 270 95% 95%;         /* #F3E8FF */
  }

  * {
    @apply border-border;
  }

  body {
    @apply bg-background text-foreground antialiased;
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
  }
}
```

Also add `Source Serif 4` font in `layout.tsx`:

```tsx
import { Inter } from "next/font/google";
// Add this import:
import { Source_Serif_4 } from "next/font/google";

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-serif",
  weight: ["400", "600", "700"],
});

// In the body tag, add sourceSerif.variable to the className
```

### COMPLETE PAGE SPECIFICATIONS

Below is the exact layout, HTML structure, and behavior for every page. Match these exactly.

---

## PAGE 1: HOME (`/` -> `src/app/page.tsx`)

**Layout:** Full-height flex column. Nav at top, hero strip, centered landing-main (max-width 700px), trust bar footer.

**Visual structure:**

```
_________________________________________________________________
| NAV: [A] AgentFlow    [Home] [Workflows] KR|
|_______________________________________________________________|
|                                                               |
|  Extract structured data from any document  <- Source Serif 4, 30px, "any document" in teal italic
|  Upload invoices, receipts, reports – or   <- 14px, muted color, max-w 520px centered
|  forward them via email. AI extracts...                       |
|                                                               |
|  +---------------------------------------+                    |
|  |  ↑                                    |  <- Upload zone: 2px dashed border, 28px padding
|  |  Drop files here or click to upload   |                    |
|  |  PDF, PNG, JPG - up to 10 files       |                    |
|  +---------------------------------------+                    |
|                                                               |
|  [invoice_q2.pdf x] [vendor_acme.pdf x]   <- File chips in surface-2 bg
|                                                               |
|  [Invoice] [Resume] [Contract] [Medical]  <- Template chips: 5px 12px, 11px, 6px radius
|  [Receipt] [Purchase Order] [Financial]     Active: primary border + primary-soft bg
|                                                               |
|  ————— or describe your task —————                            |
|                                                               |
|  [Extract vendor name, amount, due da...]                    |
|                             [Run ->]                          |
|                                                               |
|  No signup required · 5 docs free · ...                       |
|_______________________________________________________________|
```

**Key differences from current:**

- Remove "How it works" 3-card section
- Remove AGENT_TYPES badges
- Hero: 'Source Serif 4' font, `<em>` tag for teal italic on "any document"
- Template picker: flat chip row (not 2-column cards). Fetch from API, display as small chips
- Task: single `<input>` in a flex row with Run button (not textarea in a Card)
- Trust bar at bottom

**Template chips:** Fetch from `listTemplates()` API. Render as:

```tsx
<button className={cn(
  "px-3 py-1.5 rounded-md text-[11px] font-semibold border transition-all",
  "border-border bg-card hover:border-primary hover:bg-primary/5",
  isActive && "border-primary bg-primary/10 text-primary"
)} onClick={() => handleSelect(template)}>
  {template.name}
</button>
```

---

## PAGE 2: AD-HOC RESULTS (`/results/[runId]` -> `src/app/results/[runId]/page.tsx`)

**Layout:** Full-height flex column. Nav -> top bar -> export bar -> 3-column body.

**Visual structure:**

```
__________________________________________________________________
| NAV                                                                |
|____________________________________________________________________|
| [<-] | Pipeline Results                                            | <- Top bar: ghost btn, 1px divider, title
|      Invoice Parser · 3 documents · run_8f3k2 · 2.3s               | + badge-success "completed"
|____________________________________________________________________|
| [Save as Workflow] | [CSV] | [JSON] | [Email] [Sheets]             | <- Export bar: surface-2 bg
|_______________________________________________________|____________|
|  [Document] [Results]                                 |            |
| = |                                                   |  Refine    | <- Chat panel: 340px fixed width
| 3 | Stats: 3 rows · 1 flagged ·                       | "Describe what |
| f |        2.3s runtime                               |  to change"|
| i |                                                   |            |
| l |  ___________________________                      | [Refining all| <- Teal badge
| e | | Vendor  | Invoice | ... |                       |  3 docs]   |
| s | | Acme    | INV-... | ... |                       |            |
|   | |_________|_________|_____|                       | agent: Extracted|
|   |                                                   | user: also ext..|
|   | (Document tab: PDF preview                        | agent: ✓ Added..|
|   |  with highlights - placeholder)                   |            |
|   |                                                   | [textarea] |
|   |                                                   | [Send]     |
|___|___________________________________________________|____________|
```

**Docs strip (left, 36px wide):** Collapsed by default. Shows ≡ icon + "3 files" vertical text. On click, slides open a 180px panel with file list. Clicking a file switches to Document tab and closes panel.

**Tabs:** "Document" and "Results" tabs. Results is active by default. Uses underline-style tabs (2px bottom border on active, teal color).

**Stats row:** Only 3 stats: "rows extracted", "flagged", "runtime". Small pills with border.

**Results table:** Sticky header, uppercase 10px labels, hover row highlights in primary-softer.

**Flag cells:** Small colored dots (6px circles) - red for flags, green for clean.

**Document tab:** Shows a mock PDF viewer with:

- Gray background (#F5F5F4)
- White "page" card with shadow
- Extracted fields wrapped in `.pdf-highlight` spans (teal 15% bg + teal border)
- Page nav at bottom: ← 1/2 →

**Chat panel (right, 340px):**

- Header: "Refine" title, description, teal badge "Refining all N docs"
- Messages: user messages dark bg right-aligned, agent messages surface-2 left-aligned
- ✓ checkmarks in green for agent confirmations
- Input: textarea with 7px border-radius, Send button

**Key differences from current:**

- Remove `TemplateVersionPanel` completely (versions only on workflow detail)
- Remove `RunSummaryStats` (replace with inline stats row)
- Remove save-as-workflow Card at bottom (move to export bar modal)
- Results page is now full-height 3-column, not scrolling stacked cards

**Export bar actions:**

- "Save as Workflow" -> opens save-workflow-modal (teal button)
- "CSV" -> calls `downloadCsv()`
- "JSON" -> calls `downloadJson()`
- "Email" -> opens email-modal
- "Sheets" -> opens sheets-modal

---

## PAGE 3: WORKFLOWS (`/workflows` -> `src/app/workflows/page.tsx`)

**Layout:** Nav -> page-header -> scrollable 3-column card grid.

```
|-------------------------------------------------------|
| NAV                                                   |
|-------------------------------------------------------|
| Workflows                             [+ New Workflow]| <- Page header: Source Serif 4, 18px
| Your saved extraction pipelines                       |
|-------------------------------------------------------|
| ┌─────────┐  ┌─────────┐  ┌─────────┐                 | <- 3-column grid, 12px gap
| │WF       │  │WF       │  │WF       │                 |
| │Active   │  │No inbnd │  │No inbnd │                 |
| │         │  │         │  │         │                 |
| │Invoice  │  │Resume   │  │Contract │                 | <- Card: 20px padding, radius-lg
| │Parser   │  │Screener │  │Analyzer │                 |
| │desc...  │  │desc...  │  │desc...  │                 |
| │         │  │         │  │         │                 |
| │email@.. │  │         │  │         │                 | <- Inbound badge if configured
| ├─────────┤  ├─────────┤  ├─────────┤                 |
| │47 runs  │  │12 runs  │  │8 runs   │                 | <- Footer: meta + step pills
| │OCR>Ex>R │  │Txt>Ex>C │  │Txt>Ex>J │                 |
| └─────────┘  └─────────┘  └─────────┘                 |
|-------------------------------------------------------|
```

**Workflow card structure:**

- Top row: "WF" monogram (36px square, surface-2 bg, 10px radius) + status badge (Active/No inbound/Email + Sheets)
- Name: 14px bold
- Description: 12px muted
- Inbound badge (if configured): blue-soft bg, blue text, email address
- Footer: border-top, meta text (runs · version · last run) + pipeline step pills (9px font, surface-2 bg)

**On card click:** Navigate to `/workflows/{id}`

---

## PAGE 4: WORKFLOW DETAIL (`/workflows/[workflowId]` -> `src/app/workflows/[workflowId]/page.tsx`)

**Layout:** Nav -> page-header -> 2-column CSS grid (1fr + 300px sidebar).

```
 ___________________________________________________________
| NAV                                                       |
|___________________________________________________________|
|                                                           |
| [+] | Invoice Parser                  Active              | <- Page header
|     Extract vendor, amount... • v3 • 47 runs              |
|___________________________________________________________|
|                       |                                   |
| MAIN (left, scrollable)| SIDEBAR (right)                   |
|                       |                                   |
|  ___________________  | [Workflow Settings]               | <- Settings button
| |                   | |                                   |
| | Run on new files  | | OUTPUT PATHS                      |
| |                   | |  • Email team@co..                | <- success-soft bg
| |  _______________  | |  • Push to Sheets                 | <- blue-soft bg
| | |               | | |                                   |
| | | ↑ Drop files  | | | INGESTION PATHS                   |
| | |   here        | | | UI Upload  ✓ active               |
| | | Uses v3       | | | Inbound Email ✓ active            |
| | | same pipe     | | |                                   |
| | |_______________| | | VERSIONS                          |
| |                   | | v3 • current                      | <- current has left border
| | [flow-8f3k@inge..]| | | Added payment_status            |
| |___________________| | v2                                |
|                       | Added rule: flag >50K             |
| Run History           | v1                                |
|                       | Initial - vendor...               |
|  ___________________  |                                   |
| | ↑ 3 invoices - Q2 | | PIPELINE STEPS                    |
| |   batch           | | ● Text Extract                    |
| | 2h ago • upload   | |     ↓                             |
| |       • done      | | ● Field Extractor                 |
| |___________________| |     ↓                             |
|                       | ● Rules Agent                     |
|                       |     ↓                             |
|                       | ● Formatter                       |
|_______________________|___________________________________|
```

**Run history items:**

- Each run: surface bg, border, 14px padding, flex row
- Left: icon (30px square, colored bg) + name + meta
- Right: source badge (upload/email/api/scheduled) + status badge + "View ->" ghost button
- Icon symbols: ↑ for upload, @ for email, ! for failed
- "View ->" navigates to `/workflows/{id}/runs/{runId}`

**Sidebar sections:**

- Section titles: 11px, uppercase, 0.05em letter-spacing, muted color
- Settings button: 12px font, surface-2 bg, border, full width
- Output paths: success-soft/blue-soft colored rows
- Ingestion paths: rows with "active" badges
- Versions: version-item cards (current has left teal border + primary-softer bg)
- Pipeline steps: vertical list with ↓ arrows between, dot bullets

---

## PAGE 4b: WORKFLOW RESULTS (`/workflows/[workflowId]/runs/[runId]` -> NEW FILE)

**Same 3-column layout as ad-hoc results, but with these differences:**

| Feature | Ad-Hoc | Workflow Results |
|---|---|---|
| Back button | New Run -> `/` | Back to Workflow -> `/workflows/{id}` |
| Save action | "Save as Workflow" (teal) | "Save as New Version" (teal) |
| Version badge | None | "v3" teal badge next to status |
| Email/Sheets modals | Empty fields | Pre-filled from workflow settings |
| Chat badge | "Refining all N docs" | "Refining all N docs · v3" |

---

## PAGE 4c: WORKFLOW SETTINGS (`/workflows/[workflowId]/settings` -> NEW FILE)

**Layout:** Nav -> page-header -> scrollable account-layout (max-width 680px centered).

Sections (each in an `account-card` div):

1. **General:** Name input, description input, active version dropdown, Save button
2. **Default Delivery:** Email recipient input, Google Sheets URL input, sheet name input, Update button
3. **Inbound Email:** Blue-soft box with forwarding address + Copy button + explanation text
4. **Versions:** List of all versions. Current version: primary-softer bg, 3px left teal border, "current" badge. Others: border, bg. Each has editable name input + timestamp. Non-current have "Set as current" button.
5. **Danger Zone:** Red-bordered card with Archive and Delete

---

## PAGE 5: ACCOUNT (`/account` -> `src/app/account/page.tsx`)

**Layout:** Nav -> page-header -> scrollable account-layout (max-width 680px centered).

Sections:

1. **Plan & Usage** (highlighted card with primary-softer bg, primary border):
   - "Free Plan" title + "Resets Aug 31" + "Upgrade ->" teal button
   - 2x2 grid of progress bars: Pipeline runs (72/100), Documents (214/500), Workflows (4/5), Emails (18/50)
   - Each bar: 6px height, border radius 3px, primary fill (warning for near-limit)

2. **Profile:** Avatar circle (48px, primary bg, white initials) + Name, Email, Password fields (read-only display) + Edit Profile / Change Password buttons

3. **Integrations:** List of service connections:
   - Email (Resend): ✓ Connected badge + Configure button
   - Google Sheets: ✓ Connected badge + Configure button
   - Webhook: Coming soon badge, dashed border

4. **API Access:** Dimmed card (opacity 0.65), "Coming soon" badge

5. **Danger Zone:** Red-bordered card, Delete Account button

---

## NAV BAR (`src/components/nav-bar.tsx` — replaces `app-header.tsx`)

```
|                                                |
| [A] AgentFlow      [Home] [Workflows]     [KR] |
|  ↑ logo-icon        ↑ nav-links            ↑ avatar
|  26px square                              32px circle
|  dark bg, white A                         primary bg
|________________________________________________|
```

- **Logo:** 26px square, dark bg (#1C1917), white "A", 6px radius
- **Nav links:** 13px, 6px 12px padding, 6px radius. Active: surface-2 bg, 600 weight
- **No "Account" in nav links** — Account is in avatar dropdown only
- **Avatar:** 32px circle, primary bg, white initials (first letters of first+last name)
- **Avatar dropdown (on click, toggle hidden):**
  - User info: name (13px 600) + email (11px muted)
  - Separator
  - "Account Settings" button
  - "Integrations" button
  - Separator
  - "Sign Out" button (destructive color)
- **Click outside closes dropdown**

---

## MODALS

All modals share the same structure:

```tsx
// Modal overlay: fixed, full screen, rgba(0,0,0,0.35), backdrop-blur(2px), z-300
// Modal body: white bg, radius-lg, 24px padding, 400px width, shadow
// Click overlay to close, click modal body stops propagation
```

**6 modals total:**

### 1. Email Modal (ad-hoc)

- Title: "Email Results"
- Desc: "Send a formatted table + CSV attachment"
- Fields: email input, subject input
- Note: "Sends HTML table in body + CSV as attachment via Resend"
- Actions: Cancel (secondary), Send Email -> (primary)

### 2. Sheets Modal (ad-hoc)

- Title: "Push to Google Sheets"
- Desc: "Write rows directly to a spreadsheet"
- Fields: URL input, sheet name input
- Note: "Share the spreadsheet with agentflow@...iam first"
- Actions: Cancel (secondary), Push to Sheets -> (primary)

### 3. Save Workflow Modal (ad-hoc results)

- Title: "Save as Workflow"
- Desc: "Reuse this pipeline on new uploads without re-planning"
- Fields: name input, description input
- Note: "Saves current pipeline steps + extraction prompt as v1"
- Actions: Cancel (secondary), Save Workflow -> (teal)

### 4. Save Version Modal (workflow results)

- Title: "Save as New Version"
- Desc: "Save your refinements as v{N+1} of {workflow_name}"
- Fields: version name input
- Note: "Creates a new version with the refined extraction template. This becomes the active version for future runs."
- Actions: Cancel (secondary), Save Version -> (teal)

### 5. WF Email Modal (workflow results – pre-filled)

- Same as Email Modal but fields pre-filled from workflow settings
- Note includes link: "Pre-filled from workflow settings · Change default ->"

### 6. WF Sheets Modal (workflow results – pre-filled)

- Same as Sheets Modal but fields pre-filled from workflow settings
- Note includes link: "Pre-filled from workflow settings · Change default ->"

---

## API CLIENT CHANGES (`src/lib/api.ts`)

### Remove these functions:

- `getRunTemplateVersions`
- `getRunTemplateVersion`
- `revertRunToVersion`

### Add these functions:

```typescript
export async function emailResults(
  runId: string,
  toEmail: string,
  subject: string,
): Promise<{ status: string; email_id: string; message: string }> {
  return request(`/api/runs/${runId}/email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ to_email: toEmail, subject }),
  });
}

export async function pushToSheets(
  runId: string,
  spreadsheetUrl: string,
  sheetName: string,
): Promise<{ status: string; message: string }> {
  return request(`/api/runs/${runId}/sheets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ spreadsheet_url: spreadsheetUrl, sheet_name: sheetName }),
  });
}

export async function updateWorkflowFromRun(
  workflowId: string,
  runId: string,
  versionName: string,
): Promise<{ current_template_version_id: string }> {
  return request(`/api/workflows/${workflowId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ run_id: runId, version_name: versionName }),
  });
}

export async function updateWorkflowSettings(
  workflowId: string,
  data: {
    name?: string;
    description?: string;
    default_email?: string;
    default_sheets_url?: string;
    default_sheet_name?: string;
  },
): Promise<WorkflowResponse> {
  return request(`/api/workflows/${workflowId}/settings`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}
```

---

## FILE-BY-FILE INSTRUCTIONS

### Files to DELETE:

- `src/components/app-header.tsx` (replaced by nav-bar.tsx)
- `src/components/template-version-panel.tsx` (versions only on workflow detail sidebar now)

### Files to CREATE (new):

1. `src/components/nav-bar.tsx` — nav bar with avatar dropdown (spec above)
2. `src/components/modals/email-modal.tsx` — email results modal
3. `src/components/modals/sheets-modal.tsx` — Google Sheets modal
4. `src/components/modals/save-workflow-modal.tsx` — save as workflow modal
5. `src/components/modals/save-version-modal.tsx` — save as new version modal
6. `src/app/workflows/[workflowId]/settings/page.tsx` — workflow settings page
7. `src/app/workflows/[workflowId]/runs/[runId]/page.tsx` — workflow-scoped results page

### Files to REWRITE:

1. `src/app/globals.css` — new color palette (see CSS variables section above)
2. `src/app/layout.tsx` — add Source Serif 4 font
3. `src/app/page.tsx` — compact home (see Page 1 spec)
4. `src/app/results/[runId]/page.tsx` — 3-column layout (see Page 2 spec)
5. `src/app/workflows/page.tsx` — 3-column card grid (see Page 3 spec)
6. `src/app/workflows/[workflowId]/page.tsx` — 2-column with sidebar (see Page 4 spec)
7. `src/app/account/page.tsx` — full account page (see Page 5 spec)
8. `src/components/refine-chat.tsx` — adapt for right panel (not Card-based, use r2-chat style)
9. `src/components/template-picker.tsx` — simplify to chip row (not Card grid)
10. `src/lib/api.ts` — add/remove functions (see API section)

### Files to KEEP AS-IS:

- `src/components/upload-zone.tsx` — works fine, just used in home + rerun
- `src/components/run-display.tsx` — ResultsTable is reused, StepStatusList kept for workflow detail
- `src/components/empty-state.tsx` — keep
- `src/components/workflow-run-list.tsx` — may reuse or replace with new run-history styling
- `src/hooks/use-user.ts` — keep
- `src/hooks/use-run-polling.ts` — keep
- `src/lib/user-session.ts` — keep
- `src/lib/utils.ts` — keep
- `src/lib/toast.ts` — keep
- `src/lib/upload-limits.ts` — keep
- All `src/components/ui/*.tsx` — keep (shadcn components)

---

## CRITICAL STYLING RULES

1. **No emoji anywhere.** Use text or Unicode arrows (↑, ←, →, ↓, X, @, !, √) instead.
2. **Headings** use 'Source Serif 4' (font-serif variable). Body uses Inter.
3. **Page backgrounds:** 'var(--background)' (#FAF9F7). Cards/surfaces: white.
4. **Full-height pages:** body is 'height: 100vh; overflow: hidden; display: flex; flex-direction: column;'. Each page manages its own scrolling.
5. **Buttons:**
   - Primary (dark): 'bg-foreground text-background' with hover translateY(-1px)
   - Teal: 'bg-primary text-white'
   - Secondary: 'bg-card border' with hover bg change
   - Ghost: no bg, muted text, hover bg
6. **Badges:** 2px 8px padding, 99px radius, 10px font, 600 weight. Variants: success (green), warning (amber), blue, muted (gray).
7. **Section titles in sidebar:** 11px, uppercase, 700 weight, 0.05em letter-spacing, muted color.
8. **No max-w-5xl constraint on results pages.** They fill the viewport.

---

## BUILD ORDER

1. `globals.css` + `layout.tsx` (font + colors)
2. `nav-bar.tsx` (foundation for all pages)
3. `page.tsx` (home)
4. Modal components (used by results pages)
5. `results/[runId]/page.tsx` (ad-hoc results — most complex)
6. `workflows/page.tsx` (workflow list)
7. `workflows/[workflowId]/page.tsx` (workflow detail)
8. `workflows/[workflowId]/settings/page.tsx` (settings)
9. `workflows/[workflowId]/runs/[runId]/page.tsx` (workflow results)
10. `account/page.tsx` (account)
11. `api.ts` (add/remove functions)
12. Delete `app-header.tsx` and `template-version-panel.tsx`

Replace all imports of `AppHeader` with `NavBar` from `@/components/nav-bar`.

Now build all of this. Start with globals.css and layout.tsx, then work through each file in the build order. Create fully working, production-ready code for each file. Use existing shadcn/ui components where applicable (Button, Badge, Card, Input, Label, Table, Textarea, Progress). Use Tailwind classes — do NOT write custom CSS except in globals.css.

## --- END PROMPT ---

---

## Current State (GitHub `develop` branch)

### What exists

| File | What it does | Status |
|---|---|---|
| `src/app/page.tsx` | Home — hero, "How it works" cards, template picker, upload zone, task textarea, "Run Pipeline" button | **Working** |
| `src/app/results/[runId]/page.tsx` | Ad-hoc results — step list, results table, JSON/CSV download, refine chat, template version panel, save-as-workflow | **Working** |
| `src/app/workflows/page.tsx` | Workflow list — grid of cards, sign-in gate | **Working** |
| `src/app/workflows/[workflowId]/page.tsx` | Workflow detail — rerun panel, pipeline steps, version panel, run history | **Working** |
| `src/app/account/page.tsx` | Sign in / sign out — name + email form, localStorage session | **Working** |
| `src/app/layout.tsx` | Root layout — Inter font, Toaster | **Working** |
| `src/components/app-header.tsx` | Nav bar — Home, Workflows, Account links + user name | **Working** |
| `src/components/upload-zone.tsx` | Drag & drop file upload | **Working** |
| `src/components/refine-chat.tsx` | Chat panel for refinement | **Working** |
| `src/components/rerun-panel.tsx` | Upload zone for workflow reruns | **Working** |
| `src/components/run-display.tsx` | ResultsTable, RunSummaryStats, StepStatusList | **Working** |
| `src/components/template-picker.tsx` | Template selection grid | **Working** |
| `src/components/template-version-panel.tsx` | Version history + revert | **Working** |
| `src/components/workflow-run-list.tsx` | Run history list for workflows | **Working** |
| `src/lib/api.ts` | API client — all endpoints | **Working** |
| `src/hooks/use-user.ts` | User session from localStorage | **Working** |

### What's wrong (gap between current code and V2 preview)

1. **Layout is max-w-5xl centered column** — V2 needs full-width layouts (results page 3-column, workflow-detail 2-column with sidebar)
2. **Results page is stacked cards** — V2 needs 3-column layout: docs panel | document/results tabs | chat
3. **No document preview tab** — V2 has Document tab to view source doc alongside Results tab
4. **No export bar** — V2 has persistent action bar (Save Workflow, CSV, JSON, Email, Sheets)
5. **Nav bar has Account as tab** — V2 removes Account from nav, adds avatar dropdown
6. **Template version panel on results page** — V2 removes it (versions only on workflow detail)
7. **Account page is simple sign-in** — V2 has Plan & Usage, Profile, Integrations, API Access
8. **Workflow detail is stacked** — V2 uses 2-column with right sidebar
9. **No workflow settings page** — V2 has dedicated settings at /workflows/{id}/settings
10. **No workflow results page** — V2 has separate results view at /workflows/{id}/runs/{runId}
11. **No Email/Sheets modals** — V2 has send modals for outbound delivery
12. **Home page hero is verbose** — V2 is compact: title + subtitle + upload zone + templates

---

## Build Plan — Ordered by Impact

### Phase 1: Layout & Navigation Shell (2-3 hr)

*Everything else builds on this. Do first.*

#### 1.1 Update `layout.tsx`

- Add Source Serif 4 font for headings (alongside Inter)
- Remove `max-w-5xl` constraint from body — pages control their own width

#### 1.2 Rewrite `app-header.tsx` -> `components/nav-bar.tsx`

- Remove Account from `NAV` array
- Add avatar dropdown (user initials circle) in nav-right
- Dropdown: Account Settings, Integrations, separator, Sign Out
- Click-outside-to-close behavior
- If not signed in: show "Sign in" link instead of avatar

#### 1.3 Create shared layout components

- `components/page-header.tsx` — compact top bar with back arrow, divider, title, subtitle, badge
- `components/top-bar.tsx` — results page top bar (back arrow, title, status badge)
- `components/export-bar.tsx` — action bar (save, CSV, JSON, Email, Sheets buttons)

**Files to create:**

```
src/components/nav-bar.tsx      # NEW - replaces app-header.tsx
src/components/page-header.tsx   # NEW
src/components/top-bar.tsx      # NEW
src/components/export-bar.tsx   # NEW
```

**Files to modify:**

```
src/app/layout.tsx                # Font + remove width constraint
src/components/app-header.tsx      # DELETE (replaced by nav-bar.tsx)
```

---

### Phase 2: Home Page Redesign (1-2 hr)

#### 2.1 Simplify `page.tsx`

Current home is verbose: hero badge, "How it works" 3-column, template picker section, 2-column docs+task cards.

V2 home is compact:

```
┌─────────────────────────────────────────┐
│ Hero: title + subtitle                  │
│                                         │
│ Upload zone (↑ arrow, not emoji)       │
│ [file1.pdf x] [file2.pdf x]             │
│                                         │
│ Template chips (single row, compact)    │
│                                         │
│ — or describe your task —               │
│                                         │
│ [Task input] [Run Pipeline ->]          │
│                                         │
│ Trust bar: "No signup required..."      │
└─────────────────────────────────────────┘
```

**Changes:**

- Remove "How it works" card grid
- Remove AGENT_TYPES badges
- Hero: "Extract structured data from *any document*" + descriptive subtitle
- Template chips: flat row, no icons, smaller
- Task input: single-line text input (not textarea in a card)
- Keep upload zone, simplify styling
- Add trust bar footer

**Files to modify:**

```
src/app/page.tsx # REWRITE
src/components/template-picker.tsx # Simplify to chip row
src/components/upload-zone.tsx # Simplify styling
```

---

### Phase 3: Results Page — 3-Column Layout (3-4 hr)

*The most complex page. Core of the product.*

#### 3.1 Rewrite `results/[runId]/page.tsx`

Current: stacked cards (steps -> stats -> table -> versions -> chat -> save)
V2: 3-column real-time layout

```
TopBar: <- New Run | Pipeline Results . status
--------------------------------------------------
ExportBar: Save as Workflow | CSV | JSON | Email | Sheets|
--------------------------------------------------
|   | [Document]  [Results]        |               |
|D  |                              | Refine        |
|o  | Results tab: stats + table   | "Refining all |
|c  |                              | 3 docs"       |
|s  | Document tab: PDF/image preview|               |
|   | (placeholder for now)        | (chat messages)|
|E  |                              |               |
|   |                              | [textarea]    |
|   |                              | [Send]        |
--------------------------------------------------
```

**Components to create:**

```
src/components/results/results-layout.tsx   # NEW - 3-column flex container
src/components/results/docs-panel.tsx      # NEW - collapsible file sidebar
src/components/results/results-tab.tsx     # NEW - stats row + table
src/components/results/document-tab.tsx    # NEW - doc preview (placeholder)
src/components/results/tab-switcher.tsx    # NEW - Document | Results tabs
```

**Components to modify:**

```
src/components/refine-chat.tsx           # Adapt for right column
src/components/run-display.tsx           # Extract ResultsTable for reuse
```

**Key changes:**

- Remove TemplateVersionPanel from results page (per V2 versioning decision)
- Remove RunSummaryStats component (docs/steps redundant, replace with rows/flagged/runtime)
- Remove save-as-workflow card (move to export bar)
- Add Email and Sheets modals

#### 3.2 Create delivery modals

```
src/components/modals/email-modal.tsx      # NEW
src/components/modals/sheets-modal.tsx     # NEW
src/components/modals/save-workflow-modal.tsx # NEW
```

---

### Phase 4: Workflows Page — Card Grid (1 hr)

#### 4.1 Update `workflows/page.tsx`

Current: 2-column card grid, minimal info
V2: 3-column card grid with richer cards

Each card shows:

- WF monogram (not emoji)
- Status badge (Active / No inbound)
- Name + description
- Inbound email address (if configured)
- Footer: run count, version, last run, pipeline step pills

**Files to modify:**

```
src/app/workflows/page.tsx        # Card grid layout + richer cards
```

---

### Phase 5: Workflow Detail — 2-Column + Sidebar (2-3 hr)

#### 5.1 Rewrite `workflows/[workflowId]/page.tsx`

Current: stacked (version panel, 2-col rerun+steps, run history)
V2: left main + right sidebar

```
_________________________________________________
| PageHeader: <- Workflows | Invoice Parser | Active |
|-------------------------------------------------|
|  MAIN                         |  SIDEBAR (right)  |
|                               |                   |
|  Rerun zone (upload + email)  |  [Workflow Settings]|
|                               |  Output Paths     |
|  Run History                  |  Ingestion Paths  |
|   run 1 (upload, completed)   |  Versions (preview)|
|   run 2 (email, completed)    |  Pipeline Steps   |
|   run 3 (upload, failed)      |                   |
|_______________________________|___________________|
```

**Components to create:**

```
src/components/workflow/detail-layout.tsx  # NEW - 2-column
src/components/workflow/detail-sidebar.tsx # NEW - right sidebar
src/components/workflow/rerun-zone.tsx     # NEW (or adapt rerun-panel.tsx)
src/components/workflow/run-history.tsx    # NEW (or adapt workflow-run-list.tsx)
```

#### 5.2 Create `workflows/[workflowId]/settings/page.tsx`

New page with:

- General (name, description, active version dropdown)
- Default Delivery (email recipient, Google Sheets URL, sheet name)
- Inbound Email (forwarding address with copy button)
- Versions (all versions, editable names, set-as-current buttons)
- Danger Zone (archive, delete)

**Files to create:**

```
src/app/workflows/[workflowId]/settings/page.tsx # NEW
```

#### 5.3 Create `workflows/[workflowId]/runs/[runId]/page.tsx`

Workflow-scoped results page. Same 3-column layout as ad-hoc results but:

- Back button -> workflow detail (not home)
- "Save as New Version" instead of "Save as Workflow"
- Version badge showing which template version ran
- Email/Sheets modals pre-filled from workflow settings

**Files to create:**

```
src/app/workflows/[workflowId]/runs/[runId]/page.tsx   # NEW
src/components/modals/save-version-modal.tsx           # NEW
```

---

### Phase 6: Account Page Redesign (1-2 hr)

#### 6.1 Rewrite `account/page.tsx`

Current: sign-in/sign-out form only
V2: full-width centered layout with sections

Sections (top to bottom):

1. **Plan & Usage** — Free plan, progress bars (runs, docs, workflows, emails), upgrade CTA
2. **Profile** — avatar, name, email, change password
3. **Integrations** — Email (Resend) ✓, Google Sheets ✓, Webhook (coming soon)
4. **API Access** — coming soon placeholder
5. **Danger Zone** — delete account

**Files to modify:**

```
src/app/account/page.tsx        # REWRITE
```

---

### Phase 7: API Client Updates (1 hr)

#### 7.1 Update `lib/api.ts`

- **Remove:** `getRunTemplateVersions`, `getRunTemplateVersion`, `revertRunToVersion`
- **Add:** `emailResults(runId, to, subject)` -> `POST /api/runs/{id}/email`
- **Add:** `pushToSheets(runId, url, sheetName)` -> `POST /api/runs/{id}/sheets`
- **Add:** `updateWorkflowFromRun(workflowId, runId, versionName)` -> `PATCH /api/workflows/{id}`
- **Add:** `getWorkflowSettings(workflowId)` -> uses existing `getWorkflow`
- **Add:** `updateWorkflowSettings(workflowId, data)` -> `PATCH /api/workflows/{id}/settings`

#### 7.2 Update `lib/user-session.ts`

- Keep as-is for MVP (localStorage session)

---

## File Inventory — Complete

### New files (21)

```
src/components/nav-bar.tsx
src/components/page-header.tsx
src/components/top-bar.tsx
src/components/export-bar.tsx
src/components/results/results-layout.tsx
src/components/results/docs-panel.tsx
src/components/results/results-tab.tsx
src/components/results/document-tab.tsx
src/components/results/tab-switcher.tsx
src/components/workflow/detail-layout.tsx
src/components/workflow/detail-sidebar.tsx
src/components/workflow/rerun-zone.tsx
src/components/workflow/run-history.tsx
src/components/modals/email-modal.tsx
src/components/modals/sheets-modal.tsx
src/components/modals/save-workflow-modal.tsx
src/components/modals/save-version-modal.tsx
src/app/workflows/[workflowId]/settings/page.tsx
src/app/workflows/[workflowId]/runs/[runId]/page.tsx
src/app/globals.css    # UPDATE - add CSS variables, Source Serif 4
```

### Modified files (8)

```
src/app/layout.tsx
src/app/page.tsx
src/app/results/[runId]/page.tsx
src/app/workflows/page.tsx
src/app/workflows/[workflowId]/page.tsx
src/app/account/page.tsx
src/components/refine-chat.tsx
src/lib/api.ts
```

### Deleted files (2)

```
src/components/app-header.tsx         # Replaced by nav-bar.tsx
src/components/template-version-panel.tsx # Versions only on workflow detail sidebar now
```

---

## Build Order (recommended)

```
Phase 1: Layout shell + nav bar       (2-3 hr) <- do this first
Phase 2: Home page                    (1-2 hr)
Phase 3: Results page 3-column        (3-4 hr) <- hardest, most impact
Phase 4: Workflows page               (1 hr)
Phase 5: Workflow detail + settings   (2-3 hr)
Phase 6: Account page                 (1-2 hr)
Phase 7: API client                   (1 hr)
---------------------------------------------
                                      ~11-16 hr total
```

Each phase can be a separate PR. Phase 1 is the foundation — everything else depends on it. Phase 3 is the core product experience and takes the most time.

---

## CSS Variables (from UI-V2-PREVIEW.html)

These need to be added to `globals.css` to match the mockup's design system:

```css
:root {
  --primary: #0d9488;
  --primary-hover: #0f766e;
  --primary-soft: rgba(13,148,136,0.15);
  --primary-softer: rgba(13,148,136,0.06);
  --success: #059669;
  --success-soft: rgba(5,150,105,0.1);
  --warning: #d97706;
  --warning-soft: rgba(217,119,6,0.1);
  --destructive: #dc2626;
  --blue: #2563eb;
  --blue-soft: rgba(37,99,235,0.1);
  --teal: #0d9488;
}
```

Note: shadcn/ui already uses CSS variables — map these to the existing shadcn theme system rather than duplicating.

---

## What NOT to build (MVP scope)

- **API ingestion/output** — show "Coming soon" badge on integrations
- **PDF highlight preview** — Document tab shows basic embed/image, no field highlights
- **Scheduled reruns** — not in run history source types
- **Real-time SSE/WebSocket** — keep polling for now
- **Per-doc refinement** — always refine all docs (calibration mode)
- **Billing/payments** — Plan & Usage shows static data for now
