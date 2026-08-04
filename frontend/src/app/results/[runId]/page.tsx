"use client";

import { ArrowLeft, Download, Loader2, Save } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { AppHeader } from "@/components/app-header";
import { ResultsTable, StepStatusList } from "@/components/run-display";
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
import {
  ApiError,
  downloadCsv,
  downloadJson,
  getRun,
  saveWorkflowFromRun,
  type RunResponse,
} from "@/lib/api";
import { ensureUser, getStoredUserId } from "@/lib/user-session";

export default function ResultsPage() {
  const params = useParams();
  const runId = params.runId as string;

  const [run, setRun] = useState<RunResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workflowName, setWorkflowName] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedWorkflowId, setSavedWorkflowId] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getRun(runId);
      setRun(data);
      if (data.workflow_id) setSavedWorkflowId(data.workflow_id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load run.");
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSaveWorkflow() {
    if (!workflowName.trim()) {
      setSaveError("Enter a workflow name.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const userId = getStoredUserId() ?? (await ensureUser());
      const wf = await saveWorkflowFromRun(
        runId,
        userId,
        workflowName.trim(),
        run?.task_description ?? "",
      );
      setSavedWorkflowId(wf.workflow_id);
      await load();
    } catch (e) {
      setSaveError(
        e instanceof ApiError ? e.message : "Failed to save workflow.",
      );
    } finally {
      setSaving(false);
    }
  }

  const rows = run?.result?.rows ?? [];

  return (
    <div className="min-h-screen bg-muted/30">
      <AppHeader />
      <main className="mx-auto max-w-5xl px-4 py-8 space-y-6">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            New run
          </Link>
        </div>

        {loading && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading results…
          </div>
        )}

        {error && (
          <p className="text-destructive" role="alert">
            {error}
          </p>
        )}

        {run && (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-bold">Results</h1>
              <Badge variant={run.status === "completed" ? "default" : "destructive"}>
                {run.status}
              </Badge>
              {savedWorkflowId && (
                <Badge variant="secondary">Workflow saved</Badge>
              )}
            </div>

            <p className="text-sm text-muted-foreground">{run.task_description}</p>

            <Card>
              <CardHeader>
                <CardTitle>Pipeline steps</CardTitle>
                <CardDescription>
                  {run.steps.length} step(s) executed
                </CardDescription>
              </CardHeader>
              <CardContent>
                <StepStatusList steps={run.steps} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-start justify-between gap-4">
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
                {saveError && (
                  <p className="px-6 pb-4 text-sm text-destructive">{saveError}</p>
                )}
              </Card>
            )}
          </>
        )}
      </main>
    </div>
  );
}
