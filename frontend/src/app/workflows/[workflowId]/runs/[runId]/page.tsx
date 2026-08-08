"use client";

import { Loader2 } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ResultsLayout } from "@/components/results/results-layout";
import { useRunPolling } from "@/hooks/use-run-polling";
import { getWorkflow, type WorkflowResponse } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";

export default function WorkflowRunResultsPage() {
  const router = useRouter();
  const params = useParams();
  const workflowId = params.workflowId as string;
  const routeRunId = params.runId as string;
  const [activeRunId, setActiveRunId] = useState(routeRunId);
  const [refining, setRefining] = useState(false);
  const [workflow, setWorkflow] = useState<WorkflowResponse | null>(null);
  const chatSessionKeyRef = useRef(
    typeof window !== "undefined"
      ? `${routeRunId}-${Date.now()}`
      : routeRunId,
  );

  useEffect(() => {
    setActiveRunId(routeRunId);
    chatSessionKeyRef.current = `${routeRunId}-${Date.now()}`;
    setRefining(false);
  }, [routeRunId]);

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
    getWorkflow(workflowId)
      .then(setWorkflow)
      .catch(() => {
        /* optional */
      });
  }, [workflowId]);

  const versionLabel =
    workflow?.current_version_number != null
      ? `v${workflow.current_version_number}`
      : undefined;

  const showInitialLoader = loading && !run;

  if (showInitialLoader) {
    return (
      <div className="v2-page items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && !run) {
    return (
      <div className="v2-page items-center justify-center p-4">
        <p className="text-destructive">{error}</p>
      </div>
    );
  }

  if (!run) return null;

  return (
    <ResultsLayout
      run={run}
      isRunning={isRunning || refining}
      backHref={`/workflows/${workflowId}`}
      backLabel="Back to workflow"
      title={workflow?.name ?? "Workflow Results"}
      saveAction="version"
      workflowId={workflowId}
      versionLabel={versionLabel}
      refineRunId={activeRunId}
      chatSessionKey={chatSessionKeyRef.current}
      onRefined={(newRunId) => {
        setRefining(true);
        setActiveRunId(newRunId);
        router.replace(
          `/workflows/${workflowId}/runs/${newRunId}`,
          { scroll: false },
        );
      }}
      onVersionSaved={() => {
        router.push(`/workflows/${workflowId}`);
      }}
    />
  );
}
