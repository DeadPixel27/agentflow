"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { buttonVariants } from "@/components/ui/button";
import type { RunDocumentSummary, RunResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

interface RunHistoryProps {
  workflowId: string;
  runs: RunResponse[];
}

const STATUS_FILTERS = ["all", "completed", "failed", "running"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

function summarizeDocuments(
  documents: RunDocumentSummary[] | undefined,
  documentIds: string[],
): { title: string; fullList: string; count: number } {
  const names = (documents ?? [])
    .map((doc) => doc.filename?.trim())
    .filter((name): name is string => Boolean(name));

  const count = Math.max(documentIds.length, documents?.length ?? 0, names.length);
  const fullList = names.length ? names.join(", ") : "";
  const countLabel = `${count} document${count !== 1 ? "s" : ""}`;

  if (!names.length) {
    return { title: countLabel, fullList: "", count };
  }

  if (names.length === 1) {
    return { title: names[0], fullList, count };
  }

  if (names.length === 2) {
    return { title: `${names[0]}, ${names[1]}`, fullList, count };
  }

  const remaining = names.length - 2;
  return {
    title: `${names[0]}, ${names[1]} + ${remaining} more`,
    fullList,
    count,
  };
}

function formatRunTime(createdAt: string | null | undefined): string | null {
  if (!createdAt) return null;
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function RunHistory({ workflowId, runs }: RunHistoryProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [query, setQuery] = useState("");

  const filteredRuns = useMemo(() => {
    const q = query.trim().toLowerCase();
    return runs.filter((run) => {
      if (statusFilter !== "all" && run.status !== statusFilter) {
        return false;
      }
      if (!q) return true;
      if (run.task_description.toLowerCase().includes(q)) return true;
      return (run.documents ?? []).some((doc) =>
        (doc.filename || "").toLowerCase().includes(q),
      );
    });
  }, [runs, statusFilter, query]);

  if (!runs.length) {
    return (
      <p className="text-sm text-muted-foreground py-4">
        No runs yet. Upload files above to start.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="v2-section-title">Run History</h2>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search filenames or task…"
          className="h-9 w-full sm:w-56 rounded-md border border-border bg-card px-3 text-sm outline-none focus:border-primary"
        />
      </div>

      <div className="flex flex-wrap gap-2">
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            type="button"
            onClick={() => setStatusFilter(status)}
            className={cn(
              "px-3 py-1.5 rounded-md text-[11px] font-semibold border transition-all capitalize",
              "border-border bg-card hover:border-primary hover:bg-primary/5",
              statusFilter === status &&
                "border-primary bg-primary/10 text-primary",
            )}
          >
            {status}
          </button>
        ))}
      </div>

      {!filteredRuns.length ? (
        <p className="text-sm text-muted-foreground py-4">
          No runs match this filter.
        </p>
      ) : (
        <div className="space-y-2">
          {filteredRuns.map((run) => {
            const failed = run.status === "failed";
            const { title, fullList, count } = summarizeDocuments(
              run.documents,
              run.document_ids,
            );
            const when = formatRunTime(run.created_at);
            const countLabel = `${count} document${count !== 1 ? "s" : ""}`;
            // Avoid repeating "N documents" when that's already the title (no filenames).
            const showCountInSubtitle = title !== countLabel;
            return (
              <div
                key={run.run_id}
                title={fullList || undefined}
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
                  <p className="text-sm font-medium truncate">{title}</p>
                  <p className="text-[11px] text-muted-foreground">
                    {[when, showCountInSubtitle ? countLabel : null, run.status]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
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
      )}
    </div>
  );
}
