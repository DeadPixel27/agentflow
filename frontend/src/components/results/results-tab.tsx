"use client";

import { Loader2 } from "lucide-react";

import { ResultsTable } from "@/components/run-display";

interface ResultsTabPanelProps {
  rows: Record<string, unknown>[];
  flagCount: number;
  runtimeLabel?: string;
  isUpdating?: boolean;
}

export function ResultsTabPanel({
  rows,
  flagCount,
  runtimeLabel,
  isUpdating = false,
}: ResultsTabPanelProps) {
  return (
    <div className="relative flex flex-col flex-1 min-h-0 overflow-hidden">
      <div className="flex flex-wrap gap-2 px-4 py-3 border-b border-border">
        <span className="inline-flex items-center rounded-full border border-border px-2.5 py-0.5 text-[11px] font-medium">
          {rows.length} rows extracted
        </span>
        <span className="inline-flex items-center rounded-full border border-border px-2.5 py-0.5 text-[11px] font-medium">
          {flagCount} flagged
        </span>
        {runtimeLabel && (
          <span className="inline-flex items-center rounded-full border border-border px-2.5 py-0.5 text-[11px] font-medium">
            {runtimeLabel}
          </span>
        )}
      </div>
      <div className="flex-1 overflow-auto p-4">
        <ResultsTable rows={rows} />
      </div>
      {isUpdating && (
        <div className="absolute inset-0 flex items-center justify-center bg-background/60 backdrop-blur-[1px]">
          <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2 text-sm text-muted-foreground shadow-sm">
            <Loader2 className="h-4 w-4 animate-spin" />
            Updating results…
          </div>
        </div>
      )}
    </div>
  );
}
