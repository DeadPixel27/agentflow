"use client";

import { Loader2, Plus, Trash2, Workflow } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { Button, buttonVariants } from "@/components/ui/button";
import { useSignIn } from "@/hooks/use-sign-in";
import { useUser } from "@/hooks/use-user";
import {
  ApiError,
  deleteWorkflow,
  getUserWorkflows,
  type WorkflowSummary,
} from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";
import { cn } from "@/lib/utils";

function WorkflowCard({
  workflow,
  onDeleted,
}: {
  workflow: WorkflowSummary;
  onDeleted: (workflowId: string) => void;
}) {
  const [deleting, setDeleting] = useState(false);

  async function handleDelete(event: React.MouseEvent) {
    event.preventDefault();
    event.stopPropagation();

    const confirmed = window.confirm(
      `Delete "${workflow.name}"? This cannot be undone.`,
    );
    if (!confirmed) return;

    setDeleting(true);
    try {
      await deleteWorkflow(workflow.workflow_id);
      toastSuccess("Workflow deleted.");
      onDeleted(workflow.workflow_id);
    } catch (e) {
      toastError(e instanceof ApiError ? e.message : "Failed to delete workflow.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <Link
      href={`/workflows/${workflow.workflow_id}`}
      className="flex flex-col rounded-lg border border-border bg-card p-5 hover:border-primary/40 hover:shadow-sm transition-all"
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-surface-2 text-[11px] font-bold">
          WF
        </span>
        <div className="flex items-center gap-1.5">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-7 w-7 p-0 text-muted-foreground hover:text-destructive"
            disabled={deleting}
            onClick={(event) => void handleDelete(event)}
            aria-label={`Delete ${workflow.name}`}
          >
            {deleting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" />
            )}
          </Button>
        </div>
      </div>
      <h2 className="text-sm font-bold leading-snug">{workflow.name}</h2>
      <p className="text-xs text-muted-foreground mt-1 line-clamp-2 min-h-[2rem]">
        {workflow.description || "No description"}
      </p>
      <div className="mt-auto pt-4 border-t border-border flex items-center justify-between gap-2">
        <span className="text-[10px] text-muted-foreground">
          {workflow.step_count} {workflow.step_count === 1 ? "step" : "steps"}
        </span>
      </div>
    </Link>
  );
}

export default function WorkflowsPage() {
  const { user, ready } = useUser();
  const { openSignIn } = useSignIn();
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
    <div className="v2-page">
      <PageHeader
        title="Workflows"
        description="Your saved extraction pipelines"
        action={
          <Link href="/" className={cn(buttonVariants({ size: "sm" }))}>
            <Plus className="mr-1.5 h-4 w-4" />
            New Workflow
          </Link>
        }
      />

      <main className="flex-1 overflow-y-auto px-4 sm:px-6 py-6">
        {!ready && (
          <div className="flex justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {ready && !user && (
          <div className="max-w-md mx-auto text-center space-y-4 py-12">
            <p className="text-muted-foreground text-sm">
              Sign in to save and view workflows.
            </p>
            <Button type="button" onClick={openSignIn}>
              Sign in
            </Button>
          </div>
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
            <Link href="/" className={cn(buttonVariants())}>
              Start a new run
            </Link>
          </EmptyState>
        )}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 max-w-6xl">
          {workflows.map((wf) => (
            <WorkflowCard
              key={wf.workflow_id}
              workflow={wf}
              onDeleted={(workflowId) =>
                setWorkflows((prev) =>
                  prev.filter((item) => item.workflow_id !== workflowId),
                )
              }
            />
          ))}
        </div>
      </main>
    </div>
  );
}
