# Frontend V3 — Plan Mode Refinement Chat

> **What this is:** One-shot Cursor prompt. Add Plan Mode to the refine chat panel.
> All changes in `frontend/`. ~2-3 hours total.
>
> **How to use:** Paste from START to END into Cursor.

---

## --- START PROMPT ---

You are adding Plan Mode to the AgentFlow refinement chat. Codebase: `github.com/kabirrao2002/agentflow`, branch `develop`, working in `frontend/`.

### Stack

- Next.js 14 (App Router), TypeScript, Tailwind CSS 3.4, shadcn/ui, Lucide React icons

### Problem

Currently, every chat message in the refine panel immediately triggers:

1. Expensive refiner LLM call (70b model + full pipeline context)
2. Full re-extraction of ALL documents

If the user's request is vague ("fix the dates"), the refiner guesses wrong, user sends another message, another expensive re-run. 3 messages = 3 full re-extractions.

### Solution — Plan Mode

Add a cheap clarification layer before the expensive re-run:

1. User types message → hits NEW `POST /api/runs/{id}/refine/plan` endpoint (cheap 8b model)
2. Agent responds with what it understood + planned changes
3. User can chat more (still cheap) or click **[Apply]** to trigger the real re-run
4. Apply calls the EXISTING `POST /api/runs/{id}/refine` with the accumulated instruction

### New Backend Endpoint (already built in Backend V3)

```
POST /api/runs/{run_id}/refine/plan
Body: { message: string, chat_history: [{role, content}] }
Response: {
  ready: boolean,           // true = Apply button should appear
  message: string,          // assistant response to display
  planned_changes: string[], // bullet list of changes
  accumulated_instruction: string // send this to /refine when applying
}
```

Existing endpoint unchanged:

```
POST /api/runs/{run_id}/refine
Body: { message: string }
Response: { run: RunResponse, refine_summary: string }
```

---

### TASK 1: Add API Client Function

**File:** `src/lib/api.ts`

Add types and function alongside the existing `refineRun`:

```typescript
// --- Plan Mode types ---

export interface RefinePlanMessage {
  role: "user" | "assistant";
  content: string;
}

export interface RefinePlanResponse {
  ready: boolean;
  message: string;
  planned_changes: string[];
  accumulated_instruction: string;
}

export async function refinePlan(
  runId: string,
  message: string,
  chatHistory: RefinePlanMessage[],
): Promise<RefinePlanResponse> {
  return request<RefinePlanResponse>(`/api/runs/${runId}/refine/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      chat_history: chatHistory,
    }),
  });
}
```

**Do NOT modify `refineRun()`** — Apply still uses it.

---

### TASK 2: Rewrite `refine-chat.tsx` with Plan Mode

**File:** `src/components/refine-chat.tsx`

Replace the ENTIRE file with:

```tsx
"use client";

import { Check, Loader2, MessageSquare, Play, Send } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import {
  ApiError,
  refineRun,
  refinePlan,
  type RefinePlanMessage,
} from "@/lib/api";
import { toastError } from "@/lib/toast";
import { cn } from "@/lib/utils";

interface ChatMessage {
  role: "user" | "assistant";
  text: string;
  planned_changes?: string[];
}

interface RefineChatPanelProps {
  runId: string;
  disabled?: boolean;
  documentCount?: number;
  versionLabel?: string;
  variant?: "card" | "panel";
  onRefined: (newRunId: string, summary: string) => void;
}

export function RefineChatPanel({
  runId,
  disabled,
  documentCount = 1,
  versionLabel,
  variant = "card",
  onRefined,
}: RefineChatPanelProps) {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [readyToApply, setReadyToApply] = useState(false);
  const [accumulatedInstruction, setAccumulatedInstruction] = useState("");

  // Build chat_history for the plan endpoint from our local history
  function buildPlanHistory(): RefinePlanMessage[] {
    return history.map((item) => ({ role: item.role, content: item.text }));
  }

  async function handleSend() {
    const text = message.trim();
    if (!text || loading || applying) return;

    setLoading(true);
    setMessage("");
    setHistory((prev) => [...prev, { role: "user", text }]);

    try {
      const result = await refinePlan(runId, text, buildPlanHistory());

      setHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          text: result.message,
          planned_changes: result.planned_changes,
        },
      ]);

      if (result.ready && result.accumulated_instruction) {
        setReadyToApply(true);
        setAccumulatedInstruction(result.accumulated_instruction);
      } else {
        setReadyToApply(false);
        setAccumulatedInstruction("");
      }
    } catch (e) {
      toastError(e instanceof ApiError ? e.message : "Plan mode failed.");
      setHistory((prev) => prev.slice(0, -1));
      setMessage(text);
    } finally {
      setLoading(false);
    }
  }

  async function handleApply() {
    if (!accumulatedInstruction || applying) return;

    setApplying(true);
    setHistory((prev) => [
      ...prev,
      { role: "assistant", text: "⏳ Applying changes and re-running extraction..." },
    ]);

    try {
      const result = await refineRun(runId, accumulatedInstruction);
      setHistory((prev) => {
        // Replace the "applying..." message with the real summary
        const updated = prev.slice(0, -1);
        return [
          ...updated,
          { role: "assistant", text: `✓ ${result.refine_summary}` },
        ];
      });
      setReadyToApply(false);
      setAccumulatedInstruction("");
      onRefined(result.run.run_id, result.refine_summary);
    } catch (e) {
      toastError(e instanceof ApiError ? e.message : "Refine failed.");
      // Remove the "applying..." message
      setHistory((prev) => prev.slice(0, -1));
    } finally {
      setApplying(false);
    }
  }

  const badgeText = versionLabel
    ? `Refining all ${documentCount} docs · ${versionLabel}`
    : `Refining all ${documentCount} docs`;

  const chatMessages = (
    <div className="flex-1 overflow-y-auto space-y-2 p-4 min-h-0">
      {history.length === 0 && (
        <p className="text-xs text-muted-foreground">
          Describe what to change — I&apos;ll clarify and plan before
          re-running.
        </p>
      )}
      {history.map((item, index) => (
        <div key={index}>
          <div
            className={cn(
              "rounded-lg px-3 py-2 text-sm max-w-[90%]",
              item.role === "user"
                ? "ml-auto bg-foreground text-background"
                : "bg-surface-2 text-foreground",
            )}
          >
            {item.role === "assistant" && item.text.startsWith("✓") ? (
              <span className="text-green-600">{item.text}</span>
            ) : (
              item.text
            )}
          </div>
          {/* Show planned changes as pills */}
          {item.planned_changes && item.planned_changes.length > 0 && (
            <div className="mt-1.5 space-y-1 ml-1">
              {item.planned_changes.map((change, i) => (
                <div
                  key={i}
                  className="flex items-start gap-1.5 text-xs text-muted-foreground"
                >
                  <Check className="h-3 w-3 mt-0.5 text-primary shrink-0" />
                  <span>{change}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );

  const inputArea = (
    <div className="shrink-0 border-t border-border p-3 space-y-2">
      <Textarea
        placeholder={
          readyToApply
            ? "Looks good? Click Apply — or keep refining..."
            : 'e.g. "also extract payment_status"'
        }
        rows={3}
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        disabled={disabled || loading || applying}
        className="rounded-[7px] resize-none"
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            void handleSend();
          }
        }}
      />
      <div className="flex gap-2">
        <Button
          type="button"
          variant={readyToApply ? "outline" : "default"}
          className="flex-1"
          onClick={() => void handleSend()}
          disabled={disabled || loading || applying || !message.trim()}
        >
          {loading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Thinking...
            </>
          ) : (
            <>
              <Send className="mr-2 h-4 w-4" />
              Send
            </>
          )}
        </Button>
        {readyToApply && (
          <Button
            type="button"
            className="flex-1"
            onClick={() => void handleApply()}
            disabled={applying}
          >
            {applying ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Re-running...
              </>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4" />
                Apply
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );

  if (variant === "panel") {
    return (
      <aside className="w-[340px] shrink-0 flex flex-col border-l border-border bg-card min-h-0">
        <div className="shrink-0 p-4 border-b border-border space-y-2">
          <h2 className="font-serif text-base font-semibold">Refine</h2>
          <p className="text-xs text-muted-foreground">
            Tell me what to change — I&apos;ll plan first, then apply.
          </p>
          <span className="v2-badge-success">{badgeText}</span>
        </div>
        {chatMessages}
        {inputArea}
      </aside>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5" />
          Refine results
        </CardTitle>
        <CardDescription>
          Not quite right? Tell me what to change — I&apos;ll plan the fix
          before re-running.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {history.length > 0 && (
          <div className="space-y-2 rounded-md border bg-muted/30 p-3 text-sm max-h-48 overflow-y-auto">
            {history.map((item, index) => (
              <div key={index}>
                <p>
                  <span className="font-medium">
                    {item.role === "user" ? "You" : "Agent"}:
                  </span>{" "}
                  {item.role === "assistant" && item.text.startsWith("✓") ? (
                    <span className="text-green-600">{item.text}</span>
                  ) : (
                    item.text
                  )}
                </p>
                {item.planned_changes && item.planned_changes.length > 0 && (
                  <div className="ml-4 mt-1 space-y-0.5">
                    {item.planned_changes.map((change, i) => (
                      <p key={i} className="text-xs text-muted-foreground">
                        • {change}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        <Textarea
          placeholder={
            readyToApply
              ? "Looks good? Click Apply — or keep refining..."
              : 'e.g. "also extract payment_status and flag unpaid ones"'
          }
          rows={3}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          disabled={disabled || loading || applying}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void handleSend();
            }
          }}
        />
        <div className="flex gap-2">
          <Button
            type="button"
            variant={readyToApply ? "outline" : "default"}
            className="flex-1"
            onClick={() => void handleSend()}
            disabled={disabled || loading || applying || !message.trim()}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Thinking...
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                Send
              </>
            )}
          </Button>
          {readyToApply && (
            <Button
              type="button"
              className="flex-1"
              onClick={() => void handleApply()}
              disabled={applying}
            >
              {applying ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Re-running...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Apply
                </>
              )}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
```

---

### COMPLETE FILE CHANGE SUMMARY

#### New files: none

#### Files to modify:

| # | Path | What changes |
|---|------|--------------|
| 1 | `src/lib/api.ts` | Add `RefinePlanMessage`, `RefinePlanResponse` types + `refinePlan()` function |
| 2 | `src/components/refine-chat.tsx` | Full rewrite — Plan Mode with Send/Apply two-phase flow |

### BUILD ORDER

---

Step 1: Add types + `refinePlan()` to `src/lib/api.ts`
Step 2: Replace `src/components/refine-chat.tsx` with Plan Mode version
Step 3: Test: type a message → verify `/refine/plan` is called (not `/refine`)
Step 4: Test: click Apply → verify `/refine` is called with `accumulated_instruction`
Step 5: Test: card variant (ad-hoc results) and panel variant (V2 3-column) both work

### CRITICAL RULES

1. **Send button calls `/refine/plan`** (cheap) — **Apply button calls `/refine`** (expensive)
2. **Apply only appears when `ready: true`** — users can't accidentally trigger expensive re-runs
3. **Chat history is passed to every `/refine/plan` call** — the 8b model needs conversation context
4. **`accumulated_instruction` from the plan response is sent as `message` to `/refine`** — the existing refiner sees one clear instruction
5. **Both `card` and `panel` variants must work** — the card variant is used on the V1 results page, the panel variant on the V2 3-column layout
6. **The existing `refineRun()` API function stays unchanged** — Plan Mode adds `refinePlan()` alongside it

### UX FLOW

---

```
User opens results → sees refine panel
|
├─ Types "fix the dates" → Send
│  └─ /refine/plan → cheap 8b model responds:
│     "I'll normalize dates to YYYY-MM-DD. Currently seeing '03/15/2024'. Confirm?"
│     planned_changes: ["Normalize dates to YYYY-MM-DD"]
│     ready: false (ambiguous - might want different format)
|
├─ Types "no, DD/MM/YYYY" → Send
│  └─ /refine/plan → 8b responds:
│     "Got it. All dates → DD/MM/YYYY. Click Apply to re-run."
│     planned_changes: ["Normalize dates to DD/MM/YYYY"]
│     ready: true → [Apply] button appears
|
└─ Clicks [Apply]
   └─ /refine → 70b refiner modifies pipeline → full re-extraction (ONE time)
      └─ Results update, summary shown: "✓ Updated date format to DD/MM/YYYY"
```

**Token cost comparison (3-message refinement):**

- Without Plan Mode: 3 × (70b refiner + full re-extraction) = **3× expensive**
- With Plan Mode: 2 × (8b clarification) + 1 × (70b refiner + re-extraction) = **~1.2× expensive**

## --- END PROMPT ---

---

*Created: 2026-08-08*
*Covers: Plan Mode refinement chat UI (pairs with Backend V3 Task 10)*
*Estimated effort: 2-3 hours*
