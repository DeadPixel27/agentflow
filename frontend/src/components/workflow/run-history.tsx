"use client";

import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import type { RunResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

interface RunHistoryProps {
  workflowId: string;
  runs: RunResponse[];
}

export function RunHistory({ workflowId, runs }: RunHistoryProps) {
  if (!runs.length) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No runs yet. Upload files above to start.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      <h2 className="v2-section-title mb-3">Run History</h2>
      {runs.map((run) => {
        const failed = run.status === "failed";
        return (
          <div
            key={run.run_id}
            className="flex items-center gap-3 rounded-lg border border-border bg-card p-3.5"
          >
            <span
              className={cn(
                "flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-md text-xs font-bold",
                failed ? "bg-destructive/10 text-destructive" : "bg-surface-2",
              )}
            >
              {failed ? "!" : "↑"}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">
                {run.document_ids.length} document
                {run.document_ids.length !== 1 ? "s" : ""}
              </p>
              <p className="text-[11px] text-muted-foreground">
                upload · {run.status}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <span className="v2-badge-muted">upload</span>
              <span
                className={cn(
                  "text-[10px] font-semibold rounded-full px-2 py-0.5",
                  run.status === "completed"
                    ? "bg-green-100 text-green-700"
                    : run.status === "running"
                      ? "bg-muted text-muted-foreground"
                      : "bg-destructive/10 text-destructive",
                )}
              >
                {run.status}
              </span>
              <Link
                href={`/workflows/${workflowId}/runs/${run.run_id}`}
                className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
              >
                View →
              </Link>
            </div>
          </div>
        );
      })}
    </div>
  );
}
