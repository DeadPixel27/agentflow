"use client";

import { Loader2, Workflow } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { AppHeader } from "@/components/app-header";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useUser } from "@/hooks/use-user";
import { ApiError, getUserWorkflows, type WorkflowSummary } from "@/lib/api";
import { toastError } from "@/lib/toast";

export default function WorkflowsPage() {
  const { user, ready } = useUser();
  const [workflows, setWorkflows] = useState<WorkflowSummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!ready || !user) return;
    setLoading(true);
    getUserWorkflows(user.user_id)
      .then(setWorkflows)
      .catch((e) =>
        toastError(
          e instanceof ApiError ? e.message : "Failed to load workflows.",
        ),
      )
      .finally(() => setLoading(false));
  }, [user, ready]);

  return (
    <div className="min-h-screen bg-muted/30">
      <AppHeader />
      <main className="mx-auto max-w-5xl px-4 py-10 space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold">Workflows</h1>
            <p className="text-muted-foreground text-sm mt-1">
              Saved pipelines you can rerun on new uploads.
            </p>
          </div>
          <Link
            href="/"
            className="inline-flex h-9 items-center justify-center rounded-lg border border-border bg-background px-4 text-sm font-medium hover:bg-muted"
          >
            New adhoc run
          </Link>
        </div>

        {!ready && (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {ready && !user && (
          <Card>
            <CardHeader>
              <CardTitle>Sign in required</CardTitle>
              <CardDescription>
                Create an account to save and view workflows.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Link
                href="/account"
                className="inline-flex h-9 items-center justify-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Go to account
              </Link>
            </CardContent>
          </Card>
        )}

        {loading && (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {user && !loading && workflows.length === 0 && (
          <EmptyState
            icon={Workflow}
            title="No workflows yet"
            description="Run a pipeline on the home page, then save it from the results screen."
          >
            <Link
              href="/"
              className="inline-flex h-9 items-center justify-center rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Start a new run
            </Link>
          </EmptyState>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          {workflows.map((wf) => (
            <Link key={wf.workflow_id} href={`/workflows/${wf.workflow_id}`}>
              <Card className="h-full transition-colors hover:bg-muted/50">
                <CardHeader>
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-lg">{wf.name}</CardTitle>
                    <Badge variant="secondary">{wf.step_count} steps</Badge>
                  </div>
                  <CardDescription className="line-clamp-2">
                    {wf.description || "No description"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-xs text-muted-foreground font-mono">
                    {wf.workflow_id.slice(0, 8)}…
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
