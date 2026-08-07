"use client";

import { ArrowLeft, Download, Loader2, Save } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { RefineChatPanel } from "@/components/refine-chat";
import { TemplateVersionPanel } from "@/components/template-version-panel";
import { AppHeader } from "@/components/app-header";
import { ResultsTable, RunSummaryStats, StepStatusList } from "@/components/run-display";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useRunPolling } from "@/hooks/use-run-polling";
import {
  ApiError,
  downloadCsv,
  downloadJson,
  saveWorkflowFromRun,
} from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";
import { ensureUser, getStoredUserId } from "@/lib/user-session";

export default function ResultsPage() {
  const router = useRouter();
  const params = useParams();
  const runId = params.runId as string;

  const [workflowName, setWorkflowName] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedWorkflowId, setSavedWorkflowId] = useState<string | null>(null);

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
    if (run?.workflow_id) setSavedWorkflowId(run.workflow_id);
  }, [run?.workflow_id]);

  async function handleSaveWorkflow() {
    if (!workflowName.trim()) {
      toastError("Enter a workflow name.");
      return;
    }
    setSaving(true);
    try {
      const userId = getStoredUserId() ?? (await ensureUser());
      const wf = await saveWorkflowFromRun(
        runId,
        userId,
        workflowName.trim(),
        run?.task_description ?? "",
      );
      setSavedWorkflowId(wf.workflow_id);
      toastSuccess("Workflow saved.");
    } catch (e) {
      toastError(
        e instanceof ApiError ? e.message : "Failed to save workflow.",
      );
    } finally {
      setSaving(false);
    }
  }

  const rows = run?.result?.rows ?? [];
  const steps = run?.steps ?? [];
  const flagCount = rows.reduce((count, row) => {
    const flags = row.flags;
    if (Array.isArray(flags)) return count + flags.length;
    return count;
  }, 0);

  return (
    <div className="min-h-screen bg-muted/30">
      <AppHeader />
      <main className="mx-auto max-w-5xl px-4 py-8 space-y-6">
        <Link
          href="/"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-1 h-4 w-4" />
          New run
        </Link>

        {loading && !run && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading run…
          </div>
        )}

        {error && !run && (
          <p className="text-destructive" role="alert">
            {error}
          </p>
        )}

        {run && (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-bold">
                {isRunning ? "Running pipeline" : "Results"}
              </h1>
              <Badge
                variant={
                  run.status === "completed"
                    ? "default"
                    : run.status === "running"
                      ? "secondary"
                      : "destructive"
                }
              >
                {run.status}
              </Badge>
              {savedWorkflowId && (
                <>
                  <Badge variant="secondary">Workflow saved</Badge>
                  <Link
                    href={`/workflows/${savedWorkflowId}`}
                    className="text-sm text-primary hover:underline"
                  >
                    View workflow →
                  </Link>
                </>
              )}
            </div>

            <p className="text-sm text-muted-foreground">{run.task_description}</p>

            <Card>
              <CardHeader>
                <CardTitle>Pipeline steps</CardTitle>
                <CardDescription>
                  {isRunning
                    ? "Steps update live as the pipeline runs"
                    : `${steps.length} step(s) executed`}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <StepStatusList
                  steps={steps}
                  plannedSteps={run.planned_steps}
                  showProgress={isRunning}
                />
              </CardContent>
            </Card>

            {!isRunning && run.status === "completed" && (
              <RunSummaryStats
                documentCount={run.document_ids.length}
                rowCount={rows.length}
                stepCount={steps.length}
                flagCount={flagCount}
              />
            )}

            {!isRunning && (
              <>
                <Card>
                  <CardHeader className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div>
                      <CardTitle>Extracted data</CardTitle>
                      <CardDescription>
                        {rows.length} row(s) · {run.document_ids.length} document(s)
                      </CardDescription>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={!rows.length}
                        onClick={() => downloadJson(`run-${runId}.json`, rows)}
                      >
                        <Download className="mr-1 h-4 w-4" />
                        JSON
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={!rows.length}
                        onClick={() => downloadCsv(`run-${runId}.csv`, rows)}
                      >
                        <Download className="mr-1 h-4 w-4" />
                        CSV
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <ResultsTable rows={rows} />
                  </CardContent>
                </Card>

                {run.status === "completed" && (
                  <>
                    <TemplateVersionPanel
                      scopeType="run"
                      scopeId={runId}
                      currentVersionId={run.current_template_version_id}
                    />
                    <RefineChatPanel
                    runId={runId}
                    disabled={isRunning}
                    onRefined={(newRunId) => {
                      router.push(`/results/${newRunId}`);
                    }}
                    />
                  </>
                )}

                {!savedWorkflowId && run.status === "completed" && (
                  <Card>
                    <CardHeader>
                      <CardTitle>Save as workflow</CardTitle>
                      <CardDescription>
                        Reuse this pipeline on new uploads without re-planning.
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col sm:flex-row gap-3">
                      <div className="flex-1 space-y-2">
                        <Label htmlFor="wf-name">Workflow name</Label>
                        <Input
                          id="wf-name"
                          placeholder="Resume extraction"
                          value={workflowName}
                          onChange={(e) => setWorkflowName(e.target.value)}
                          disabled={saving}
                        />
                      </div>
                      <Button
                        className="sm:self-end"
                        onClick={handleSaveWorkflow}
                        disabled={saving}
                      >
                        {saving ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <Save className="mr-2 h-4 w-4" />
                        )}
                        Save workflow
                      </Button>
                    </CardContent>
                  </Card>
                )}

                {run.status === "failed" && run.error_message && (
                  <Card className="border-destructive/50">
                    <CardContent className="pt-6">
                      <p className="text-sm text-destructive">{run.error_message}</p>
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
