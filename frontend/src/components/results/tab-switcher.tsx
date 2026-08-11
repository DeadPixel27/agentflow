"use client";

import { cn } from "@/lib/utils";

export type ResultsTab = "document" | "results";

interface TabSwitcherProps {
  active: ResultsTab;
  onChange: (tab: ResultsTab) => void;
}

export function TabSwitcher({ active, onChange }: TabSwitcherProps) {
  const tabs: { id: ResultsTab; label: string }[] = [
    { id: "document", label: "Document" },
    { id: "results", label: "Results" },
  ];

  return (
    <div className="flex gap-4 border-b border-border px-4">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          onClick={() => onChange(tab.id)}
          className={cn(
            "pb-2 text-sm font-medium transition-colors border-b-2 -mb-px",
            active === tab.id
              ? "border-primary text-primary"
              : "border-transparent text-muted-foreground hover:text-foreground",
          )}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
