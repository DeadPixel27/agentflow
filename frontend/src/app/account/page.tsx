"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { GoogleSignInButton } from "@/components/google-sign-in-button";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useUser } from "@/hooks/use-user";
import { ApiError, getUserUsage, type UsageSummary } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";
import {
  clearStoredUser,
  isEmailAuthAllowed,
  signInUser,
  signInWithGoogle,
} from "@/lib/user-session";
import { cn } from "@/lib/utils";

function AccountCard({
  title,
  children,
  highlight,
  danger,
  dimmed,
}: {
  title: string;
  children: React.ReactNode;
  highlight?: boolean;
  danger?: boolean;
  dimmed?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-5 space-y-4",
        highlight && "border-primary/30 bg-primary/5",
        danger && "border-destructive/40",
        dimmed && "opacity-65",
      )}
    >
      <h2 className="font-serif text-base font-semibold">{title}</h2>
      {children}
    </div>
  );
}

function UsageBar({ label, used, limit }: { label: string; used: number; limit: number }) {
  const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  const warning = pct >= 80;
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span>{label}</span>
        <span className="text-muted-foreground tabular-nums">
          {used}/{limit}
        </span>
      </div>
      <div className="h-1.5 rounded-sm bg-muted overflow-hidden">
        <div
          className={cn(
            "h-full rounded-sm transition-all",
            warning ? "bg-amber-500" : "bg-primary",
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  return (parts[0]?.[0] ?? "A").toUpperCase();
}

export default function AccountPage() {
  const router = useRouter();
  const { user, ready, setUser } = useUser();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const allowEmailAuth = isEmailAuthAllowed();

  useEffect(() => {
    if (user) {
      getUserUsage()
        .then(setUsage)
        .catch(() => {
          /* silent fail - show defaults */
        });
    }
  }, [user]);

  function handleSignOut() {
    clearStoredUser();
    setUser(null);
    toastSuccess("Signed out.");
  }

  const finishSignIn = useCallback(
    (signedIn: { name: string }, isNewUser: boolean) => {
      toastSuccess(
        isNewUser
          ? `Welcome, ${signedIn.name}!`
          : `Welcome back, ${signedIn.name}!`,
      );
      router.push("/workflows");
    },
    [router],
  );

  async function handleSignIn(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      toastError("Name is required.");
      return;
    }
    if (!email.trim()) {
      toastError("Email is required to sign in.");
      return;
    }
    setLoading(true);
    try {
      const { user: signedIn, isNewUser } = await signInUser(name, email);
      setUser(signedIn);
      finishSignIn(signedIn, isNewUser);
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Failed to sign in.");
    } finally {
      setLoading(false);
    }
  }

  const handleGoogleCredential = useCallback(
    async (idToken: string) => {
      setLoading(true);
      try {
        const { user: signedIn, isNewUser } = await signInWithGoogle(idToken);
        setUser(signedIn);
        finishSignIn(signedIn, isNewUser);
      } catch (err) {
        toastError(
          err instanceof ApiError ? err.message : "Google sign-in failed.",
        );
      } finally {
        setLoading(false);
      }
    },
    [finishSignIn, setUser],
  );

  if (!ready) {
    return (
      <div className="v2-page items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="v2-page">
        <PageHeader
          title="Sign in"
          description="Sign in to run documents, save workflows, and sync results."
        />
        <main className="flex-1 overflow-y-auto px-4 py-6">
          <div className="mx-auto max-w-[480px] space-y-4">
            <AccountCard title="Continue with Google">
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">
                  You can browse templates on the home page without an account.
                  Sign in when you&apos;re ready to upload and run.
                </p>
                <GoogleSignInButton
                  onCredential={handleGoogleCredential}
                  disabled={loading}
                />
                {allowEmailAuth && (
                  <>
                    <div className="relative py-1">
                      <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t" />
                      </div>
                      <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-card px-2 text-muted-foreground">
                          or email
                        </span>
                      </div>
                    </div>
                    <form onSubmit={handleSignIn} className="space-y-4">
                      <div className="space-y-2">
                        <Label htmlFor="name">Name</Label>
                        <Input
                          id="name"
                          value={name}
                          onChange={(e) => setName(e.target.value)}
                          disabled={loading}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <Input
                          id="email"
                          type="email"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          disabled={loading}
                          required
                        />
                      </div>
                      <Button type="submit" className="w-full" disabled={loading}>
                        {loading && (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        )}
                        Sign in / Create account
                      </Button>
                    </form>
                  </>
                )}
              </div>
            </AccountCard>
            <p className="text-center text-sm text-muted-foreground">
              <Link href="/" className="text-primary hover:underline">
                Back to home
              </Link>
            </p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="v2-page">
      <PageHeader title="Account" description="Manage your profile and integrations" />
      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-[680px] space-y-6">
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
                  Upgrade →
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
                You&apos;ve hit your free limit.{" "}
                <Link href="/pricing" className="underline">
                  Join the Pro waitlist
                </Link>{" "}
                for unlimited access.
              </p>
            )}
          </AccountCard>

          <AccountCard title="Profile">
            <div className="flex items-center gap-4">
              <span className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-lg font-bold text-primary-foreground">
                {initials(user.name)}
              </span>
              <div className="text-sm space-y-0.5">
                <p className="font-semibold">{user.name}</p>
                <p className="text-muted-foreground">{user.email || "—"}</p>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Name</Label>
                <Input value={user.name} readOnly />
              </div>
              <div className="space-y-1">
                <Label className="text-xs text-muted-foreground">Email</Label>
                <Input value={user.email} readOnly />
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" disabled>
                Edit Profile
              </Button>
              <Button variant="outline" size="sm" disabled>
                Change Password
              </Button>
              <Button variant="outline" size="sm" onClick={handleSignOut}>
                Sign out
              </Button>
            </div>
          </AccountCard>

          <AccountCard title="Integrations">
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-md border px-3 py-2.5 text-sm">
                <span>Email (Resend)</span>
                <div className="flex items-center gap-2">
                  <span className="v2-badge-success">Connected</span>
                  <Button variant="outline" size="sm" disabled>
                    Configure
                  </Button>
                </div>
              </div>
              <div className="flex items-center justify-between rounded-md border px-3 py-2.5 text-sm">
                <span>Google Sheets</span>
                <div className="flex items-center gap-2">
                  <span className="v2-badge-success">Connected</span>
                  <Button variant="outline" size="sm" disabled>
                    Configure
                  </Button>
                </div>
              </div>
              <div className="flex items-center justify-between rounded-md border border-dashed px-3 py-2.5 text-sm opacity-70">
                <span>Webhook</span>
                <span className="v2-badge-muted">Coming soon</span>
              </div>
            </div>
          </AccountCard>

          <AccountCard title="API Access" dimmed>
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Programmatic access to runs and workflows.
              </p>
              <span className="v2-badge-muted">Coming soon</span>
            </div>
          </AccountCard>

          <AccountCard title="Danger Zone" danger>
            <p className="text-sm text-muted-foreground">
              Permanently delete your account and all workflows.
            </p>
            <Button variant="destructive" size="sm" disabled>
              Delete Account
            </Button>
          </AccountCard>
        </div>
      </main>
    </div>
  );
}
