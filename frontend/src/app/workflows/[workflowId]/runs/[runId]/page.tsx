"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ResultsLayout } from "@/components/results/results-layout";
import { useRunPolling } from "@/hooks/use-run-polling";
import { getWorkflow, type WorkflowResponse } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";

export default function WorkflowRunResultsPage() {
  const router = useRouter();
  const params = useParams();
  const workflowId = params.workflowId as string;
  const runId = params.runId as string;

  const [workflow, setWorkflow] = useState<WorkflowResponse | null>(null);

  const { run, loading, error, isRunning } = useRunPolling(runId, {
    onComplete: (data) => {
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

  if (loading && !run) {
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
      isRunning={isRunning}
      backHref={`/workflows/${workflowId}`}
      backLabel="Back to workflow"
      title={workflow?.name ?? "Workflow Results"}
      saveAction="version"
      workflowId={workflowId}
      versionLabel={versionLabel}
      onRefined={(newRunId) =>
        router.push(`/workflows/${workflowId}/runs/${newRunId}`)
      }
    />
  );
}
