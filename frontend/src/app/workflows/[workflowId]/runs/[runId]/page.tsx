"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useRunResultsContext } from "@/components/results/run-results-context";
import { useRunPolling } from "@/hooks/use-run-polling";
import { getWorkflow, type WorkflowResponse } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";

export default function WorkflowRunResultsPage() {
  const router = useRouter();
  const params = useParams();
  const workflowId = params.workflowId as string;
  const { activeRunId, refining, setRefining, setRunState, setPageConfig } =
    useRunResultsContext();
  const [workflow, setWorkflow] = useState<WorkflowResponse | null>(null);

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

  useEffect(() => {
    setPageConfig({
      backHref: `/workflows/${workflowId}`,
      backLabel: "Back to workflow",
      title: workflow?.name ?? "Workflow Results",
      saveAction: "version",
      workflowId,
      versionLabel,
      onVersionSaved: () => {
        router.push(`/workflows/${workflowId}`);
      },
    });
  }, [workflow, workflowId, versionLabel, router, setPageConfig]);

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
