"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { NavBar } from "@/components/nav-bar";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useUser } from "@/hooks/use-user";
import { ApiError } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";
import { clearStoredUser, signInUser } from "@/lib/user-session";
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
  const pct = Math.min(100, Math.round((used / limit) * 100));
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

  function handleSignOut() {
    clearStoredUser();
    setUser(null);
    toastSuccess("Signed out.");
  }

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
      toastSuccess(
        isNewUser
          ? `Welcome, ${signedIn.name}!`
          : `Welcome back, ${signedIn.name}!`,
      );
      router.push("/workflows");
    } catch (err) {
      toastError(err instanceof ApiError ? err.message : "Failed to sign in.");
    } finally {
      setLoading(false);
    }
  }

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
        <NavBar />
        <PageHeader title="Account" description="Sign in to save workflows" />
        <main className="flex-1 overflow-y-auto px-4 py-6">
          <div className="mx-auto max-w-[480px]">
            <AccountCard title="Sign in">
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
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Sign in / Create account
                </Button>
              </form>
            </AccountCard>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="v2-page">
      <NavBar />
      <PageHeader title="Account" description="Manage your profile and integrations" />
      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-[680px] space-y-6">
          <AccountCard title="Plan & Usage" highlight>
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="font-semibold text-sm">Free Plan</p>
                <p className="text-xs text-muted-foreground">Resets Aug 31</p>
              </div>
              <Button size="sm" variant="outline" disabled>
                Upgrade →
              </Button>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <UsageBar label="Pipeline runs" used={72} limit={100} />
              <UsageBar label="Documents" used={214} limit={500} />
              <UsageBar label="Workflows" used={4} limit={5} />
              <UsageBar label="Emails" used={18} limit={50} />
            </div>
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
