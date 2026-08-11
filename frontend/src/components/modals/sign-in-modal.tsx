"use client";

import { Loader2 } from "lucide-react";
import { useCallback, useState } from "react";

import { GoogleSignInButton } from "@/components/google-sign-in-button";
import { ModalShell } from "@/components/modals/modal-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useUser } from "@/hooks/use-user";
import { ApiError } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";
import {
  isEmailAuthAllowed,
  signInUser,
  signInWithGoogle,
  type StoredUser,
} from "@/lib/user-session";

interface SignInModalProps {
  open: boolean;
  onClose: () => void;
  onSignedIn: (user: StoredUser, isNewUser: boolean) => void | Promise<void>;
}

export function SignInModal({ open, onClose, onSignedIn }: SignInModalProps) {
  const { setUser } = useUser();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const allowEmailAuth = isEmailAuthAllowed();

  const finish = useCallback(
    async (signedIn: StoredUser, isNewUser: boolean) => {
      setUser(signedIn);
      toastSuccess(
        isNewUser
          ? `Welcome, ${signedIn.name}!`
          : `Welcome back, ${signedIn.name}!`,
      );
      await onSignedIn(signedIn, isNewUser);
    },
    [onSignedIn, setUser],
  );

  async function handleEmailSignIn(e: React.FormEvent) {
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
      await finish(signedIn, isNewUser);
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
        await finish(signedIn, isNewUser);
      } catch (err) {
        toastError(
          err instanceof ApiError ? err.message : "Google sign-in failed.",
        );
      } finally {
        setLoading(false);
      }
    },
    [finish],
  );

  return (
    <ModalShell
      open={open}
      onClose={loading ? () => undefined : onClose}
      title="Sign in"
      description="Sign in to run documents, save workflows, and sync results."
      className="max-w-[420px]"
    >
      <div className="space-y-4">
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
            <form onSubmit={handleEmailSignIn} className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="sign-in-name">Name</Label>
                <Input
                  id="sign-in-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sign-in-email">Email</Label>
                <Input
                  id="sign-in-email"
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
    </ModalShell>
  );
}
