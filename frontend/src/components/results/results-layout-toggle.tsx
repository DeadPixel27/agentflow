"use client";

import { LayoutList, Table2 } from "lucide-react";

import type { ResultsLayout } from "@/components/results/results-layout";
import { cn } from "@/lib/utils";

interface ResultsLayoutToggleProps {
  value: ResultsLayout;
  onChange: (layout: ResultsLayout) => void;
}

export function ResultsLayoutToggle({
  value,
  onChange,
}: ResultsLayoutToggleProps) {
  return (
    <div
      className="inline-flex items-center rounded-md border border-border bg-background p-0.5"
      role="group"
      aria-label="Results layout"
    >
      <button
        type="button"
        onClick={() => onChange("vertical")}
        className={cn(
          "inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium transition-colors",
          value === "vertical"
            ? "bg-primary/10 text-primary"
            : "text-muted-foreground hover:text-foreground",
        )}
        aria-pressed={value === "vertical"}
        title="Vertical field list"
      >
        <LayoutList className="h-3.5 w-3.5" />
        Vertical
      </button>
      <button
        type="button"
        onClick={() => onChange("horizontal")}
        className={cn(
          "inline-flex items-center gap-1 rounded px-2 py-1 text-[11px] font-medium transition-colors",
          value === "horizontal"
            ? "bg-primary/10 text-primary"
            : "text-muted-foreground hover:text-foreground",
        )}
        aria-pressed={value === "horizontal"}
        title="Horizontal table"
      >
        <Table2 className="h-3.5 w-3.5" />
        Horizontal
      </button>
    </div>
  );
}
