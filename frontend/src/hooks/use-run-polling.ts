"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, getRun, type RunResponse } from "@/lib/api";

const POLL_MS = 1500;

interface UseRunPollingOptions {
  enabled?: boolean;
  onComplete?: (run: RunResponse) => void;
  onError?: (message: string) => void;
}

export function useRunPolling(
  runId: string,
  { enabled = true, onComplete, onError }: UseRunPollingOptions = {},
) {
  const [run, setRun] = useState<RunResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const completedRef = useRef(false);

  const fetchRun = useCallback(async () => {
    try {
      const data = await getRun(runId);
      setRun(data);
      setError(null);

      if (data.status !== "running" && !completedRef.current) {
        completedRef.current = true;
        onComplete?.(data);
      }
      return data;
    } catch (e) {
      const message =
        e instanceof ApiError ? e.message : "Failed to load run.";
      setError(message);
      onError?.(message);
      return null;
    }
  }, [runId, onComplete, onError]);

  useEffect(() => {
    if (!enabled || !runId) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      setLoading(true);
      const data = await fetchRun();
      if (cancelled) return;
      setLoading(false);

      if (data?.status === "running") {
        timer = setTimeout(poll, POLL_MS);
      }
    }

    completedRef.current = false;
    void poll();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [enabled, runId, fetchRun]);

  const isRunning = run?.status === "running";
  const completedSteps =
    run?.steps.filter((s) => s.status === "completed").length ?? 0;
  const totalSteps = run?.steps.length ?? 0;
  const progress =
    totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

  return {
    run,
    loading,
    error,
    isRunning,
    progress,
    completedSteps,
    totalSteps,
    refresh: fetchRun,
  };
}
