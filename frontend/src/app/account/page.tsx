"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AppHeader } from "@/components/app-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useUser } from "@/hooks/use-user";
import { ApiError } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";
import { clearStoredUser, signInUser } from "@/lib/user-session";

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
      toastError(
        err instanceof ApiError ? err.message : "Failed to sign in.",
      );
    } finally {
      setLoading(false);
    }
  }

  if (!ready) {
    return (
      <div className="min-h-screen bg-muted/30">
        <AppHeader />
        <main className="mx-auto max-w-lg px-4 py-16 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <AppHeader />
      <main className="mx-auto max-w-lg px-4 py-10 space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Account</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Workflows live in Supabase and are tied to your email. This browser
            only remembers your session (user id) in localStorage.
          </p>
        </div>

        {user && (
          <Card>
            <CardHeader>
              <CardTitle>Signed in</CardTitle>
              <CardDescription>Current session on this device</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                <span className="text-muted-foreground">Name:</span> {user.name}
              </p>
              <p>
                <span className="text-muted-foreground">Email:</span>{" "}
                {user.email || "—"}
              </p>
              <p className="font-mono text-xs text-muted-foreground break-all">
                {user.user_id}
              </p>
              <Button variant="outline" size="sm" onClick={handleSignOut}>
                Sign out
              </Button>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>{user ? "Switch account" : "Sign in"}</CardTitle>
            <CardDescription>
              Same email always restores your workflows from the database.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSignIn} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  placeholder="Kabir Yadav"
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
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  required
                />
              </div>
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                {user ? "Sign in as different user" : "Sign in / Create account"}
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
