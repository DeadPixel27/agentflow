"use client";

import { Loader2, Plus, Workflow } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/empty-state";
import { NavBar } from "@/components/nav-bar";
import { PageHeader } from "@/components/page-header";
import { buttonVariants } from "@/components/ui/button";
import { useUser } from "@/hooks/use-user";
import {
  ApiError,
  getUserWorkflows,
  type WorkflowSummary,
} from "@/lib/api";
import { toastError } from "@/lib/toast";
import { cn } from "@/lib/utils";

function WorkflowCard({ workflow }: { workflow: WorkflowSummary }) {
  const steps = Array.from({ length: workflow.step_count }, (_, i) => `S${i + 1}`);

  return (
    <Link
      href={`/workflows/${workflow.workflow_id}`}
      className="flex flex-col rounded-lg border border-border bg-card p-5 hover:border-primary/40 hover:shadow-sm transition-all"
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-surface-2 text-[11px] font-bold">
          WF
        </span>
        <span className="v2-badge-muted">Active</span>
      </div>
      <h2 className="text-sm font-bold leading-snug">{workflow.name}</h2>
      <p className="text-xs text-muted-foreground mt-1 line-clamp-2 min-h-[2rem]">
        {workflow.description || "No description"}
      </p>
      <div className="mt-auto pt-4 border-t border-border flex items-center justify-between gap-2">
        <span className="text-[10px] text-muted-foreground">
          {workflow.step_count} steps
        </span>
        <div className="flex flex-wrap gap-1 justify-end">
          {steps.slice(0, 4).map((s, i) => (
            <span
              key={i}
              className="rounded px-1.5 py-0.5 text-[9px] font-medium bg-surface-2"
            >
              {s}
            </span>
          ))}
        </div>
      </div>
    </Link>
  );
}

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
    <div className="v2-page">
      <NavBar />
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
            <Link href="/account" className={cn(buttonVariants())}>
              Go to account
            </Link>
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
            <WorkflowCard key={wf.workflow_id} workflow={wf} />
          ))}
        </div>
      </main>
    </div>
  );
}
