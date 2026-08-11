"use client";

import { useEffect, useState } from "react";

import { useRunResultsContext } from "@/components/results/run-results-context";
import { useRunPolling } from "@/hooks/use-run-polling";
import { toastError, toastSuccess } from "@/lib/toast";

export default function ResultsPage() {
  const { activeRunId, refining, setRefining, setRunState, setPageConfig } =
    useRunResultsContext();
  const [savedWorkflowId, setSavedWorkflowId] = useState<string | null>(null);

  const { run, loading, error, isRunning } = useRunPolling(activeRunId, {
    onComplete: (data) => {
      if (data.run_id === activeRunId) {
        setRefining(false);
      }
      if (data.status === "completed") {
        toastSuccess("Pipeline finished successfully.");
      } else if (data.status === "failed") {
        toastError(data.error_message ?? "Pipeline failed.");
      }
    },
    onError: (msg) => toastError(msg),
  });

  useEffect(() => {
    if (run?.workflow_id) setSavedWorkflowId(run.workflow_id);
  }, [run?.workflow_id]);

  useEffect(() => {
    setPageConfig({
      backHref: "/",
      backLabel: "New run",
      saveAction: savedWorkflowId ? "none" : "workflow",
      workflowId: savedWorkflowId ?? undefined,
      onWorkflowSaved: (workflowId) => setSavedWorkflowId(workflowId),
    });
  }, [savedWorkflowId, setPageConfig]);

  useEffect(() => {
    setRunState({
      run,
      isRunning: isRunning || refining,
      loading,
      error,
    });
  }, [run, isRunning, refining, loading, error, setRunState]);

  return null;
}
