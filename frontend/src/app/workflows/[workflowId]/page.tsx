"use client";

import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AppHeader } from "@/components/app-header";
import { RerunPanel } from "@/components/rerun-panel";
import { WorkflowRunList } from "@/components/workflow-run-list";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
    load();
  }, [load]);

  return (
    <div className="min-h-screen bg-muted/30">
      <AppHeader />
      <main className="mx-auto max-w-5xl px-4 py-8 space-y-6">
        <Link
          href="/workflows"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          All workflows
        </Link>

        {loading && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading workflow…
          </div>
        )}

        {error && (
          <p className="text-destructive" role="alert">
            {error}
          </p>
        )}

        {workflow && (
          <>
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-bold">{workflow.name}</h1>
                <Badge variant="secondary">{workflow.steps.length} steps</Badge>
                <Badge variant="outline">{workflow.source}</Badge>
              </div>
              {workflow.description && (
                <p className="text-muted-foreground">{workflow.description}</p>
              )}
              <p className="text-sm text-muted-foreground">
                {workflow.task_description}
              </p>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <RerunPanel
                workflowId={workflow.workflow_id}
                workflowName={workflow.name}
              />

              <Card>
                <CardHeader>
                  <CardTitle>Pipeline steps</CardTitle>
                  <CardDescription>Saved plan (planner skipped on rerun)</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {workflow.steps.map((step) => (
                    <div
                      key={step.step_order}
                      className="rounded-lg border px-3 py-2 text-sm"
                    >
                      <p className="font-medium">
                        {step.step_order}. {step.agent_type}
                      </p>
                      <p className="text-muted-foreground text-xs mt-1">
                        {step.reason}
                      </p>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Run history</CardTitle>
                <CardDescription>
                  {runs.length} run(s) for this workflow
                </CardDescription>
              </CardHeader>
              <CardContent>
                <WorkflowRunList runs={runs} />
              </CardContent>
            </Card>
          </>
        )}
      </main>
    </div>
  );
}
