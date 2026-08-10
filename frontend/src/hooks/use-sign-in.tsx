"use client";

import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { ProcessingOverlay } from "@/components/modals/processing-overlay";
import { SignInModal } from "@/components/modals/sign-in-modal";
import { useUser } from "@/hooks/use-user";
import { ApiError, SESSION_EXPIRED_EVENT } from "@/lib/api";
import { hasPendingRun } from "@/lib/pending-run";
import { resumePendingRun } from "@/lib/resume-pending-run";
import { toastError } from "@/lib/toast";

interface SignInContextValue {
  openSignIn: () => void;
  closeSignIn: () => void;
}

const SignInContext = createContext<SignInContextValue | null>(null);

export function SignInProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { setUser } = useUser();
  const [open, setOpen] = useState(false);
  const [processing, setProcessing] = useState(false);

  const openSignIn = useCallback(() => setOpen(true), []);
  const closeSignIn = useCallback(() => setOpen(false), []);

  useEffect(() => {
    function onSessionExpired() {
      setUser(null);
      setOpen(true);
    }
    window.addEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
    return () =>
      window.removeEventListener(SESSION_EXPIRED_EVENT, onSessionExpired);
  }, [setUser]);

  const handleSignedIn = useCallback(async () => {
    setOpen(false);

    if (!hasPendingRun()) {
      return;
    }

    setProcessing(true);
    try {
      const runId = await resumePendingRun();
      if (runId) {
        router.push(`/results/${runId}`);
        return;
      }
    } catch (err) {
      toastError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Could not start your run. Please try again.",
      );
    } finally {
      setProcessing(false);
    }
  }, [router]);

  const value = useMemo(
    () => ({ openSignIn, closeSignIn }),
    [openSignIn, closeSignIn],
  );

  return (
    <SignInContext.Provider value={value}>
      {children}
      <SignInModal
        open={open}
        onClose={closeSignIn}
        onSignedIn={handleSignedIn}
      />
      <ProcessingOverlay
        open={processing}
        message="Processing your request…"
      />
    </SignInContext.Provider>
  );
}

export function useSignIn(): SignInContextValue {
  const ctx = useContext(SignInContext);
  if (!ctx) {
    throw new Error("useSignIn must be used within a SignInProvider");
  }
  return ctx;
}
