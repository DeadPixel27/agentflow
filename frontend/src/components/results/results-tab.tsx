"use client";

import { ResultsTable } from "@/components/run-display";

interface ResultsTabPanelProps {
  rows: Record<string, unknown>[];
  flagCount: number;
  runtimeLabel?: string;
}

export function ResultsTabPanel({
  rows,
  flagCount,
  runtimeLabel,
}: ResultsTabPanelProps) {
  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
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
    </div>
  );
}
