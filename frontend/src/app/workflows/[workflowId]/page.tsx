"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { DetailLayout } from "@/components/workflow/detail-layout";
import { DetailSidebar } from "@/components/workflow/detail-sidebar";
import { RerunZone } from "@/components/workflow/rerun-zone";
import { RunHistory } from "@/components/workflow/run-history";
import {
  ApiError,
  getWorkflow,
  getWorkflowRuns,
  type RunResponse,
  type WorkflowResponse,
} from "@/lib/api";

export default function WorkflowDetailPage() {
  const params = useParams();
  const workflowId = params.workflowId as string;

  const [workflow, setWorkflow] = useState<WorkflowResponse | null>(null);
  const [runs, setRuns] = useState<RunResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [wf, runList] = await Promise.all([
        getWorkflow(workflowId),
        getWorkflowRuns(workflowId),
      ]);
      setWorkflow(wf);
      setRuns(runList);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load workflow.");
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading && !workflow) {
    return (
      <div className="v2-page items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !workflow) {
    return (
      <div className="v2-page">
        <main className="p-6">
          <p className="text-destructive">{error ?? "Workflow not found."}</p>
          <Link href="/workflows" className="text-sm text-primary hover:underline mt-2 inline-block">
            Back to workflows
          </Link>
        </main>
      </div>
    );
  }

  const versionLabel =
    workflow.current_version_number != null
      ? `v${workflow.current_version_number}`
      : undefined;

  return (
    <DetailLayout
      header={
        <div className="shrink-0 border-b border-border px-4 sm:px-6 py-5">
            <Link
              href="/workflows"
              className="text-xs text-muted-foreground hover:text-foreground mb-2 inline-block"
            >
              ← All workflows
            </Link>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="font-serif text-lg font-semibold">{workflow.name}</h1>
              {versionLabel && (
                <span className="v2-badge-success">{versionLabel}</span>
              )}
            </div>
            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
              {workflow.description || workflow.task_description}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {runs.length} runs · {workflow.steps.length} steps
            </p>
          </div>
      }
      main={
        <>
          <RerunZone
            workflowId={workflow.workflow_id}
            workflowName={workflow.name}
            versionLabel={versionLabel}
          />
          <RunHistory workflowId={workflow.workflow_id} runs={runs} />
        </>
      }
      sidebar={
        <DetailSidebar workflow={workflow} onWorkflowUpdated={load} />
      }
    />
  );
}
