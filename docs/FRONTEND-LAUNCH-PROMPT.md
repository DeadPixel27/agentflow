# Frontend Launch — Bug Fixes + JWT Auth + Usage + Waitlist + Pricing + Extraction UI

> Transcribed from `frontend-launch-prompt/` screenshots (Aug 9, 2026).


> **What this is:** One-shot Cursor prompt. Fix 3 refine-chat bugs, add JWT auth flow, real usage tracking, waitlist form, pricing page, confidence badges, validation
warnings, OCR engine info. All changes in `frontend/`. ~17 hours total.
>
> **How to use:** Paste from START to END into Cursor. Run AFTER the backend launch prompt.

---
## --- START PROMPT ---

You are fixing refine-chat bugs and adding auth, usage, waitlist, and pricing features to the AgentFlow frontend. Codebase: `github.com/kabirrao2002/agentflow`, branch
`develop`, working in `frontend/`.

### What this covers (15 tasks):
1. Fix focus lost after sending refine chat message
2. Fix duplicate preview panels in refine chat
3. Fix page-refresh feel after Apply refinement
4. JWT auth flow - store token, send with all requests, handle 401
5. Update sign-in to store JWT from new response
6. Add API client functions (getUserUsage, joinWaitlist)
7. "Try with sample" button on template picker
8. Wire real usage data to account page
9. Hard cap modal (usage limit)
10. Waitlist form + pricing page
11. Error handling UI (friendly toasts by HTTP status)
12. Nav bar - add Pricing link
13. Display per-field confidence badges in results table
14. Show validation warnings on results
15. Show OCR engine info in document panel
### Critical rules:
- Backend returns JWT in `POST /api/auth/session` response as `{user, token, is_new_user, auth_provider}`
- ALL API requests (except auth + waitlist + health) must include `Authorization: Bearer <token>`
- Handle 401 -> redirect to sign-in, 429 -> usage limit modal, 503 -> "service busy" toast
- The account page already has a `UsageBar` component and "Plan & Usage" card - wire to real API data
- Existing UI library: shadcn/ui, Tailwind, Lucide icons, sonner toasts

---

### TASK 1: Fix focus lost after sending refine chat message

**File:** `src/components/refine-chat.tsx`

**Root cause:** The focus `useEffect` fires before the DOM settles after `readyToApply` state change renders the Apply button, stealing focus.

Find the existing focus effect:

```typescript
  useEffect(() => {
    if (!loading && !applying && !disabled) {
      textareaRef.current?.focus();
    }
  }, [loading, applying, disabled]);
```

REPLACE with:

```typescript
  useEffect(() => {
    if (!loading && !applying && !disabled) {
      // Use requestAnimationFrame to ensure focus happens after DOM settles
      // (Apply button rendering can steal focus on state change)
      requestAnimationFrame(() => {
        textareaRef.current?.focus();
      });
    }
  }, [loading, applying, disabled, readyToApply, history.length]);
```

Also, in the `handleSend` function, add explicit refocus in the `finally` block. Find:

```typescript
    } finally {
      setLoading(false);
    }
```

REPLACE with:

```typescript
    } finally {
      setLoading(false);
      // Explicit refocus after all state updates settle
      requestAnimationFrame(() => {
        textareaRef.current?.focus();
      });
    }
```


---
### TASK 2: Fix duplicate preview panels

**File:** `src/components/refine-chat.tsx`

**Root cause:** Preview is shown TWICE - once inside the chat message (`item.preview`) AND once standalone at the bottom (`readyToApply && preview.length > 0`).

Find this block inside the `chatMessages` JSX (it's after the `history.map` block, still inside the scrollable div):

```tsx
      {readyToApply && preview.length > 0 && (
        <PreviewPanel preview={preview} />
      )}
```

DELETE this entire block. The preview is already attached to the assistant message in history via `item.preview`, so it renders correctly without the duplicate.

---

### TASK 3: Fix page-refresh feel after Apply refinement

**File:** `src/components/results/run-results-context.tsx`

**Root cause:** `handleRefined` calls `router.replace(newRunId)` immediately on Apply -> URL changes -> polling hook resets -> loading flicker -> pipeline panel replaces
results table -> feels like full page reload.

**Fix part A:** Defer `router.replace` until the child run completes.

Find the `handleRefined` callback:

```typescript
  const handleRefined = useCallback(
    (newRunId: string) => {
      setRefining(true);
      setActiveRunId(newRunId);
      router.replace(makeRunHref(newRunId), { scroll: false });
    },
    [makeRunHref, router],
  );
```

REPLACE with:

```typescript
  const handleRefined = useCallback(
    (newRunId: string) => {
      setRefining(true);
      setActiveRunId(newRunId);
      // Don't router.replace yet - wait until the child run completes
      // to avoid loading flicker and page-refresh feel.
      // URL will be updated in the onComplete callback.
      pendingUrlUpdateRef.current = newRunId;
    },
    [],
  );
```
Add this ref near the other refs:

```typescript
const pendingUrlUpdateRef = useRef<string | null>(null);
```

**File:** `src/app/results/[runId]/page.tsx`

In the `onComplete` callback, add the deferred URL update. Find:

```typescript
    onComplete: (data) => {
      if (data.run_id === activeRunId) {
        setRefining(false);
      }
```

REPLACE with:

```typescript
    onComplete: (data) => {
      if (data.run_id === activeRunId) {
        setRefining(false);
      }
    }
```
Actually - since `pendingUrlUpdateRef` is in the context/shell, not the page, we need to expose it. A simpler approach:

**Alternative fix for `run-results-context.tsx`:** Keep `setActiveRunId` but skip `router.replace` until completion.

Find the `useEffect` that watches `routeRunId`:

```typescript
  useEffect(() => {
    setActiveRunId(routeRunId);
    if (!refiningRef.current) {
      chatSessionKeyRef.current = `${routeRunId}-${Date.now()}`;
      setRunState(defaultRunState);
    }
  }, [routeRunId]);
```

This is fine as-is. The key change is in `handleRefined` - don't call `router.replace` there.

Instead, add a new `useEffect` that updates the URL AFTER refining completes:

```typescript
  useEffect(() => {
    // Update URL after refinement completes (deferred from handleRefined)
    if (!refining && activeRunId !== routeRunId) {
      router.replace(makeRunHref(activeRunId), { scroll: false });
    }
  }, [refining, activeRunId, routeRunId, makeRunHref, router]);
```

**Fix part B:** Show inline "Updating..." banner instead of swapping to PipelinePanel.

**File:** `src/components/results/run-results-frame.tsx`

Find the `showPipelineProgress` logic:

```typescript
const showPipelineProgress =
  !hasCompletedResults &&
  Boolean(run) &&
  (isRunning || run!.status !== "completed");
```

This is fine - when `hasCompletedResults` is true and `isRunning` (re-running), `showPipelineProgress` is false. The results table stays visible.

But the `isRerunning` variable should show a banner. Find where `isRerunning` is used. Currently `ResultsTabPanel` receives `isUpdating={isRerunning}`.

Check if `ResultsTabPanel` shows a loading indicator for `isUpdating`. If not, add one.

Find the `ResultsTabPanel` usage:

```tsx
          <ResultsTabPanel
            rows={rows}
            flagCount={flagCount}
            isUpdating={isRerunning}
          />
```

If `ResultsTabPanel` doesn't render an "Updating..." indicator, add one ABOVE the tab switcher when `isRerunning`:

```tsx
{isRerunning && (
  <div className="shrink-0 flex items-center gap-2 border-b border-primary/20 bg-primary/5 px-4 py-2 text-xs text-primary">
    <Loader2 className="h-3.5 w-3.5 animate-spin" />
    <span>Re-running extraction with your refinements...</span>
  </div>
)}
```

Place this BEFORE the `{showPipelineProgress ? ...}` conditional block, inside the `<div className="flex flex-1 flex-col min-w-0 min-h-0">`.

---

### TASK 4: JWT auth flow - store token, send with all requests



Add JWT token storage. Add this constant with the other keys:

```typescript
const TOKEN_KEY = "agentflow_token";
```

Add these functions:

```typescript
export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function saveToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}
```

Update the `clearStoredUser` function to also clear the token:

```typescript
export function clearStoredUser(): void {
  localStorage.removeItem(USER_ID_KEY);
  localStorage.removeItem(USER_NAME_KEY);
  localStorage.removeItem(USER_EMAIL_KEY);
  localStorage.removeItem(TOKEN_KEY);
}
```

Update `signInUser` to store the token. Find:

```typescript
export async function signInUser(
  name: string,
  email: string,
): Promise<{ user: StoredUser; isNewUser: boolean }> {
  const result = await signIn(name.trim(), email.trim());
  const stored: StoredUser = {
    user_id: result.user.user_id,
    name: result.user.name,
    email: result.user.email,
  };
  saveStoredUser(stored);
  return { user: stored, isNewUser: result.is_new_user };
}
...

REPLACE with:

```typescript
export async function signInUser(
  name: string,
  email: string,
): Promise<{ user: StoredUser; isNewUser: boolean }> {
  const result = await signIn(name.trim(), email.trim());
  const stored: StoredUser = {
    user_id: result.user.user_id,
    name: result.user.name,
    email: result.user.email,
  };
  saveStoredUser(stored);
  // Store JWT token for authenticated API calls
  if (result.token) {
    saveToken(result.token);
  }
  return { user: stored, isNewUser: result.is_new_user };
}
```

**File:** `src/lib/api.ts`

Update the `request` function to include the JWT token. Find:

```typescript
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
```

REPLACE with:

```typescript
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // Inject JWT token for authenticated requests
  const headers = new Headers(init?.headers);
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("agentflow_token");
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });
```

Update the `signIn` function return type. Find:

```typescript
export async function signIn(name: string, email: string): Promise<{
  user: User;
  is_new_user: boolean;
  auth_provider: string;
}> {
```

REPLACE with:

```typescript
export async function signIn(name: string, email: string): Promise<{
  user: User;
  is_new_user: boolean;
  auth_provider: string;
  token: string;
}> {
```

---

### TASK 5: Handle 401 - redirect to sign-in

**File:** `src/lib/api.ts`

In the `request` function, after the `if (!res.ok)` block, add special handling for 401:

Find:

```typescript
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        detail = body.detail ?? JSON.stringify(body);
      } catch {
        // ignore
      }
      throw new ApiError(String(detail), res.status);
    }
```

REPLACE with:

```typescript
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        detail = body.detail ?? JSON.stringify(body);
      } catch {
        // ignore
      }

      // Auto-redirect to sign-in on 401 (expired/invalid token)
      if (res.status === 401 && typeof window !== "undefined") {
        localStorage.removeItem("agentflow_token");
        localStorage.removeItem("agentflow_user_id");
        localStorage.removeItem("agentflow_user_name");
        localStorage.removeItem("agentflow_user_email");
        window.location.href = "/account";
        throw new ApiError("Session expired. Please sign in again.", 401);
      }

      throw new ApiError(String(detail), res.status);
    }
```

---

### TASK 6: Add API client functions

**File:** `src/lib/api.ts`

Add these interfaces and functions at the end of the file (before `downloadCsv`):

```typescript
// --- Usage types ---

export interface UsageSummary {
  pages_used: number;
  pages_limit: number;
  resets_at: string | null;
}

export async function getUserUsage(): Promise<UsageSummary> {
  return request<UsageSummary>("/api/users/me/usage");
}

// --- Waitlist types ---

export interface WaitlistResponse {
  message: string;
  already_joined: boolean;
}

export async function joinWaitlist(
  email: string,
  name: string = "",
  source: string = "pricing_page",
): Promise<WaitlistResponse> {
  return request<WaitlistResponse>("/api/waitlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, name, source }),
  });
}
```

---

### TASK 7: "Try with sample" button

**Step 1:** Add a sample invoice PDF.

Place a sample invoice PDF at `public/samples/sample-invoice.pdf`. You can use any clean, professional-looking invoice (not a real client document). If you don't have one, create a simple text file placeholder and note it needs to be replaced with a real PDF.

**Step 2:** Update the template picker.

**File:** `src/components/template-picker.tsx`

Add a "Try with sample" button that:
1. Fetches the sample PDF from `/samples/sample-invoice.pdf`
2. Uploads it via the `uploadFiles` API
3. Runs the invoice template via `runTemplate`
4. Navigates to `/results/{runId}`

Add this function inside the component:

```typescript
  async function handleTrySample() {
    try {
      setLoading(true);
      // Fetch the bundled sample PDF
      const response = await fetch("/samples/sample-invoice.pdf");
      const blob = await response.blob();
      const file = new File([blob], "sample-invoice.pdf", { type: "application/pdf" });

      // Upload it
      const upload = await uploadFiles([file]);

      // Run the invoice template
      const run = await runTemplate(upload.upload_id, "invoice-parser");

      // Navigate to results
      router.push(`/results/${run.run_id}`);
    } catch (e) {
      toastError(e instanceof ApiError ? e.message : "Failed to run sample.");
    } finally {
      setLoading(false);
    }
  }
```

Add a button in the UI near the template list:

```tsx
<Button
  variant="outline"
  size="sm"
  onClick={handleTrySample}
  disabled={loading}
  className="gap-2"
>
  <Play className="h-4 w-4" />
  Try with sample invoice
</Button>
```

Import `Play` from `lucide-react`, and `uploadFiles`, `runTemplate`, `ApiError` from `@/lib/api`. Import `useRouter` from `next/navigation`.

---

### TASK 8: Wire real usage data to account page

**File:** `src/app/account/page.tsx`

The account page already has a `UsageBar` component and "Plan & Usage" card with HARDCODED values. Wire it to the real API.

Add these imports:

```typescript
import { getUserUsage, type UsageSummary } from "@/lib/api";
```

Add state inside `AccountPage`:

```typescript
const [usage, setUsage] = useState<UsageSummary | null>(null);
```

Add a useEffect to fetch usage when the user is available:

```typescript
useEffect(() => {
  if (user) {
    getUserUsage()
      .then(setUsage)
      .catch(() => {/* silent fail - show defaults */});
  }
}, [user]);
```

Update the "Plan & Usage" card. Find the hardcoded usage section:

```tsx
      <AccountCard title="Plan & Usage" highlight>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="font-semibold text-sm">Free Plan</p>
            <p className="text-xs text-muted-foreground">Resets Aug 31</p>
          </div>
          <Button size="sm" variant="outline" disabled>
            Upgrade ->
          </Button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          <UsageBar label="Pipeline runs" used={72} limit={100} />
          <UsageBar label="Documents" used={214} limit={500} />
          <UsageBar label="Workflows" used={4} limit={5} />
          <UsageBar label="Emails" used={18} limit={50} />
        </div>
      </AccountCard>
```

REPLACE with:

```tsx
      <AccountCard title="Plan & Usage" highlight>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="font-semibold text-sm">Free Plan</p>
            <p className="text-xs text-muted-foreground">
              {usage?.resets_at
                ? `Resets ${new Date(usage.resets_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}`
                : "50 pages/month"}
            </p>
          </div>
          <Link href="/pricing">
            <Button size="sm" variant="outline">
              Upgrade ->
            </Button>
          </Link>
        </div>
        <div className="pt-2">
          <UsageBar
            label="Pages extracted"
            used={usage?.pages_used ?? 0}
            limit={usage?.pages_limit ?? 50}
          />
        </div>
        {usage && usage.pages_used >= usage.pages_limit && (
          <p className="text-xs text-amber-600 font-medium">
            You've hit your free limit.{" "}
            <Link href="/pricing" className="underline">Join the Pro waitlist</Link>{" "}
            for unlimited access.
          </p>
        )}
      </AccountCard>
```

Add `import Link from "next/link"` at the top.

---

### TASK 9: Hard cap modal (usage limit)

**New file:** `src/components/modals/usage-limit-modal.tsx`

Create this file with the ENTIRE content:

```tsx
"use client";

import { useRouter } from "next/navigation";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface UsageLimitModalProps {
  open: boolean;
  onClose: () => void;
  message?: string;
}

export function UsageLimitModal({ open, onClose, message }: UsageLimitModalProps) {
  const router = useRouter();

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-500" />
            <DialogTitle>Free limit reached</DialogTitle>
          </div>
          <DialogDescription>
            {message || "You've used all 50 free pages this month. Join the Pro waitlist for unlimited access."}
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-3 pt-2">
          <Button
            onClick={() => {
              onClose();
              router.push("/pricing");
            }}
          >
            Join Pro Waitlist
          </Button>
          <Button variant="outline" onClick={onClose}>
            Maybe later
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

**Usage:** Import and use in the results/run pages where extraction is triggered. When the API returns 429, show this modal:
```tsx
  const [showUsageLimit, setShowUsageLimit] = useState(false);
  const [usageLimitMessage, setUsageLimitMessage] = useState("");

  // In catch block when calling run/extraction APIs:
  if (err instanceof ApiError && err.status === 429) {
    setUsageLimitMessage(err.message);
    setShowUsageLimit(true);
  }

  // In JSX:
  <UsageLimitModal
    open={showUsageLimit}
    onClose={() => setShowUsageLimit(false)}
    message={usageLimitMessage}
  />
```

Add this pattern to:
- `src/app/page.tsx` (home page where adhoc runs start)
- `src/components/template-picker.tsx` (where template runs start)
- `src/components/refine-chat.tsx` (where refinements happen)

---


### TASK 10: Waitlist form + pricing page

**New file:** `src/app/pricing/page.tsx`

Create this file with the ENTIRE content:

```tsx
"use client";

import { Check, Loader2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, joinWaitlist } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";
import { loadStoredUser } from "@/lib/user-session";
import { cn } from "@/lib/utils";

function PricingCard({
  title,
  price,
  features,
  cta,
  highlight,
}: {
  title: string;
  price: string;
  features: string[];
  cta: React.ReactNode;
  highlight?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border p-6 space-y-5 flex flex-col",
        highlight
          ? "border-primary bg-primary/5 shadow-sm"
          : "border-border bg-card",
      )}
    >
      <div>
        <h3 className="font-serif text-lg font-semibold">{title}</h3>
        <p className="text-2xl font-bold mt-1">{price}</p>
      </div>
      <ul className="space-y-2 flex-1">
        {features.map((f, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            <Check className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <span>{f}</span>
          </li>
        ))}
      </ul>
      {cta}
    </div>
  );
}

export default function PricingPage() {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [joined, setJoined] = useState(false);

  const stored = loadStoredUser();

  async function handleJoinWaitlist(e: React.FormEvent) {
    e.preventDefault();
    const waitlistEmail = email.trim() || stored?.email || "";
    if (!waitlistEmail) {
      toastError("Email is required.");
      return;
    }

    setLoading(true);
    try {
      const result = await joinWaitlist(
        waitlistEmail,
        name.trim() || stored?.name || "",
        "pricing_page",
      );
      setJoined(true);
      toastSuccess(result.message);
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Failed to join waitlist.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="v2-page">
      <PageHeader
        title="Pricing"
        description="Extract data from any document with AI"
      />
      <main className="flex-1 overflow-y-auto px-4 py-8">
        <div className="mx-auto max-w-[800px] space-y-10">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <PricingCard
              title="Free"
              price="$0"
              features={[
                "50 pages/month",
                "All templates (invoice, receipt, contract, etc.)",
                "Chat refinement",
                "CSV & JSON export",
                "Email delivery",
                "Google Sheets push",
              ]}
              cta={
                <Link href="/">
                  <Button variant="outline" className="w-full">
                    Start extracting
                  </Button>
                </Link>
              }
            />

            <PricingCard
              title="Pro"
              price="Coming soon"
              highlight
              features={[
                "Unlimited pages",
                "Priority extraction (faster models)",
                "Custom templates",
                "API access",
                "Webhook integrations",
                "Priority support",
              ]}
              cta={
                joined ? (
                  <div className="flex items-center justify-center gap-2 py-2 text-sm text-primary font-medium">
                    <Check className="h-4 w-4" />
                    You're on the list!
                  </div>
                ) : (
                  <form onSubmit={handleJoinWaitlist} className="space-y-3">
                    {!stored?.email && (
                      <>
                        <div className="space-y-1">
                          <Label htmlFor="waitlist-email" className="text-xs">
                            Email
                          </Label>
                          <Input
                            id="waitlist-email"
                            type="email"
                            placeholder="you@company.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            disabled={loading}
                            required
                          />
                        </div>
                        <div className="space-y-1">
                          <Label htmlFor="waitlist-name" className="text-xs">
                            Name (optional)
                          </Label>
                          <Input
                            id="waitlist-name"
                            placeholder="Your name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            disabled={loading}
                          />
                        </div>
                      </>
                    )}
                    <Button type="submit" className="w-full" disabled={loading}>
                      {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      {stored?.email ? "Join waitlist" : "Join Pro waitlist"}
                    </Button>
                  </form>
                )
              }
            />
          </div>

          <div className="text-center text-sm text-muted-foreground space-y-1">
            <p>
              Questions?{" "}
              <a href="mailto:kabir@agentflow.app" className="text-primary underline">
                kabir@agentflow.app
              </a>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
```

---

### TASK 11: Error handling UI

**File:** `src/app/page.tsx` (and any other pages that call APIs)

Add consistent error handling that maps HTTP status codes to user-friendly messages. The pattern is:

```typescript
import { UsageLimitModal } from "@/components/modals/usage-limit-modal";

// In state:
const [showUsageLimit, setShowUsageLimit] = useState(false);
const [usageLimitMsg, setUsageLimitMsg] = useState("");

// In catch blocks:
try {
  // ... API call
} catch (err) {
  if (err instanceof ApiError) {
    switch (err.status) {
      case 401:
        // Already handled by api.ts (auto-redirect)
        break;
      case 429:
        setUsageLimitMsg(err.message);
        setShowUsageLimit(true);
        break;
      case 503:
        toastError("Service is temporarily at capacity. Please try again in a few minutes.");
        break;
      default:
        toastError(err.message);
    }
  } else {
    toastError("Something went wrong. Please try again.");
  }
}

// In JSX:
<UsageLimitModal
  open={showUsageLimit}
  onClose={() => setShowUsageLimit(false)}
  message={usageLimitMsg}
/>
...

Apply this pattern in:
- Home page (`src/app/page.tsx`) - if there's an adhoc run form
- Template picker component - around `runTemplate` calls
- Refine chat - around `refineRun` and `refinePlan` calls

For `refine-chat.tsx`, update `handleApply` error handling. Find:

```typescript
} catch (e) {
  toastError(e instanceof ApiError ? e.message : "Refine failed.");
}
```
REPLACE with:

```typescript
} catch (e) {
  if (e instanceof ApiError && e.status === 429) {
    toastError(e.message);
    // Optionally trigger the usage limit modal if parent provides callback
  } else if (e instanceof ApiError && e.status === 503) {
    toastError("Service is temporarily at capacity. Try again shortly.");
  } else {
    toastError(e instanceof ApiError ? e.message : "Refine failed.");
  }
}
```


### TASK 12: Nav bar - add Pricing link

**File:** `src/components/nav-bar.tsx`

Find the `NAV_LINKS` array:

```typescript
const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/workflows", label: "Workflows" },
];
```

REPLACE with:

```typescript
const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/workflows", label: "Workflows" },
  { href: "/pricing", label: "Pricing" },
];
```

---

### TASK 13: Display per-field confidence badges in results table

**File:** `src/lib/api.ts`

Update the extraction result types to include confidence and validation data. Find the existing result types and add:

```typescript
// --- Extraction result types (updated for confidence + validation) ---

export interface FieldConfidence {
  [fieldName: string]: number; // 0.0 to 1.0
}

export interface ValidationWarning {
  field: string;
  message: string;
  severity: "warning" | "error";
}

export interface ExtractedDocumentResult {
  document_id: string;
  filename: string;
  fields: Record<string, any>;
  confidence?: FieldConfidence;
  validation_warnings?: ValidationWarning[];
}
```

**File:** `src/components/results/results-tab.tsx` (or wherever the results table renders field values)

Add a confidence badge next to each field value. Create a helper component:

```tsx
function ConfidenceBadge({ score }: { score?: number }) {
  if (score === undefined || score === null) return null;

  const pct = Math.round(score * 100);
  let color: string;
  let label: string;

  if (score >= 0.9) {
    color = "bg-emerald-100 text-emerald-700 border-emerald-200";
    label = "High";
  } else if (score >= 0.7) {
    color = "bg-amber-100 text-amber-700 border-amber-200";
    label = "Medium";
  } else {
    color = "bg-red-100 text-red-700 border-red-200";
    label = "Low";
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-medium ${color}`}
      title={`Confidence: ${pct}%`}
    >
      {pct}%
    </span>
  );
}
```

In the table cell where field values are rendered, add the badge. The pattern:

```tsx
<td className="...">
  <span>{fieldValue}</span>
  {confidence && confidence[fieldName] !== undefined && (
    <ConfidenceBadge score={confidence[fieldName]} />
  )}
</td>
```

Where `confidence` is the `FieldConfidence` object from the API response for this document.

**Import `ConfidenceBadge`** in any component that renders field values in a table/grid format.

---

### TASK 14: Show validation warnings on results

**File:** `src/components/results/results-tab.tsx` (or wherever field values are displayed)

Add a warning icon for fields that have validation warnings. Create a helper:

```tsx
import { AlertTriangle, AlertCircle } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

function FieldWarning({ warnings, fieldName }: { warnings?: ValidationWarning[]; fieldName: string }) {
  if (!warnings) return null;

  const fieldWarnings = warnings.filter((w) => w.field === fieldName);
  if (fieldWarnings.length === 0) return null;

  const isError = fieldWarnings.some((w) => w.severity === "error");
  const Icon = isError ? AlertCircle : AlertTriangle;
  const color = isError ? "text-red-500" : "text-amber-500";

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Icon className={`h-3.5 w-3.5 ${color} inline-block ml-1`} />
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-[250px]">
          <ul className="text-xs space-y-1">
            {fieldWarnings.map((w, i) => (
              <li key={i}>{w.message}</li>
            ))}
          </ul>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
```

Add this alongside the confidence badge in each table cell:

```tsx
<td className="...">
  <span>{fieldValue}</span>
  <ConfidenceBadge score={confidence?.[fieldName]} />
  <FieldWarning warnings={validationWarnings} fieldName={fieldName} />
</td>
```

Also add a summary count at the top of the results panel when warnings exist:

```tsx
{validationWarnings && validationWarnings.length > 0 && (
  <div className="flex items-center gap-2 px-4 py-2 border-b border-amber-200 bg-amber-50 text-xs text-amber-700">
    <AlertTriangle className="h-3.5 w-3.5" />
    <span>
      {validationWarnings.length} field{validationWarnings.length > 1 ? "s" : ""} flagged for review
    </span>
  </div>
)}
```

---

### TASK 15: Show OCR engine info in document panel

**File:** `src/components/results/document-tab.tsx` (or wherever the document details/metadata are shown)

The backend now returns `extraction_method` for each document (values: `"pymupdf"`, `"tesseract"`, `"rapidocr"`, `"docling"`). Display this as a small badge in the
document info area.
```tsx
function ExtractionMethodBadge({ method }: { method?: string }) {
  if (!method) return null;

  const config: Record<string, { label: string; color: string }> = {
    pymupdf: { label: "Digital PDF", color: "bg-blue-100 text-blue-700" },
    tesseract: { label: "OCR (Tesseract)", color: "bg-slate-100 text-slate-700" },
    rapidocr: { label: "OCR (RapidOCR)", color: "bg-indigo-100 text-indigo-700" },
    docling: { label: "Layout-Aware", color: "bg-purple-100 text-purple-700" },
  };

  const { label, color } = config[method] ?? {
    label: method,
    color: "bg-slate-100 text-slate-600",
  };

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${color}`}>
      {label}
    </span>
  );
}
```

Place this badge near the document filename or in the document metadata section:

```tsx
<div className="flex items-center gap-2">
  <span className="text-sm font-medium truncate">{document.filename}</span>
  <ExtractionMethodBadge method={document.extraction_method} />
</div>
```

---

## File Change Summary

### New files (2):
| File | Purpose |
|---|---|
| `src/components/modals/usage-limit-modal.tsx` | Hard cap modal with waitlist CTA |
| `src/app/pricing/page.tsx` | Pricing page with free tier + Pro waitlist form |

### Modified files (11):
| File | Change |
|---|---|
| `src/components/refine-chat.tsx` | Fix focus, remove duplicate preview, improve error handling |
| `src/components/results/run-results-context.tsx` | Defer router.replace until child run completes |
| `src/components/results/run-results-frame.tsx` | Add inline "Updating..." banner during re-runs |
| `src/lib/api.ts` | Add JWT header, 401 handling, usage + waitlist API functions, extraction result types |
| `src/lib/user-session.ts` | Store/clear JWT token alongside user data |
| `src/app/account/page.tsx` | Wire real usage data to Plan & Usage card |
| `src/components/nav-bar.tsx` | Add Pricing nav link |
| `src/components/template-picker.tsx` | Add "Try with sample" button |
| `src/components/results/results-tab.tsx` | Add ConfidenceBadge + FieldWarning components, wire to API data |
| `src/components/results/document-tab.tsx` | Add ExtractionMethodBadge, show OCR engine used |
| `src/components/results/docs-panel.tsx` | Show validation warning summary banner |

### New static assets:
| File | Purpose |
|---|---|
| `public/samples/sample-invoice.pdf` | Sample invoice PDF for "Try with sample" feature |

---

## Build order:
1. `refine-chat.tsx` - fix focus + duplicate preview (Tasks 1-2)
2. `run-results-context.tsx` + `run-results-frame.tsx` - fix page refresh (Task 3)
3. `user-session.ts` - add token storage (Task 4)
4. `api.ts` - add JWT header + 401 handling + new API functions + extraction types (Tasks 4-6, 13)
5. `template-picker.tsx` - sample button (Task 7)
6. `account/page.tsx` - real usage data (Task 8)
7. `usage-limit-modal.tsx` - new file (Task 9)
8. `pricing/page.tsx` - new file (Task 10)
9. Apply error handling pattern across pages (Task 11)
10. `nav-bar.tsx` - add Pricing link (Task 12)
11. `results-tab.tsx` - confidence badges + validation warnings (Tasks 13-14)
12. `document-tab.tsx` - OCR engine badge (Task 15)

## --- END PROMPT ---

