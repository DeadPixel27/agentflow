"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, getRun, type RunResponse } from "@/lib/api";

const POLL_MS = 1500;
/** Stop aggressive polling; backend stale reclaim is 30m — FE surfaces earlier. */
const MAX_POLL_MS = 20 * 60 * 1000;
const STUCK_MESSAGE =
  "This run is taking longer than expected. It may have been interrupted — refresh or start a new extraction.";

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
  const onCompleteRef = useRef(onComplete);
  const onErrorRef = useRef(onError);

  onCompleteRef.current = onComplete;
  onErrorRef.current = onError;

  const fetchRun = useCallback(async () => {
    try {
      const data = await getRun(runId);
      setRun(data);
      setError(null);

      if (data.status !== "running" && !completedRef.current) {
        completedRef.current = true;
        onCompleteRef.current?.(data);
      }
      return data;
    } catch (e) {
      const message =
        e instanceof ApiError ? e.message : "Failed to load run.";
      setError(message);
      onErrorRef.current?.(message);
      return null;
    }
  }, [runId]);

  useEffect(() => {
    if (!enabled || !runId) return;

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const startedAt = Date.now();

    completedRef.current = false;
    setLoading((prev) => (run === null ? true : prev));

    async function poll() {
      const data = await fetchRun();
      if (cancelled) return;
      setLoading(false);

      if (data?.status !== "running") return;

      if (Date.now() - startedAt >= MAX_POLL_MS) {
        setError(STUCK_MESSAGE);
        onErrorRef.current?.(STUCK_MESSAGE);
        return;
      }

      timer = setTimeout(poll, POLL_MS);
    }

    void poll();

    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only reset loading when runId changes
  }, [enabled, runId, fetchRun]);

  const isRunning =
    run?.run_id === runId
      ? run.status === "running"
      : run !== null;
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
