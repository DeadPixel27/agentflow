"use client";

import { Menu } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";

export interface DocFile {
  id: string;
  name: string;
}

interface DocsPanelProps {
  files: DocFile[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function DocsPanel({ files, selectedId, onSelect }: DocsPanelProps) {
  const [open, setOpen] = useState(false);

  if (!files.length) return null;

  return (
    <div className="relative flex shrink-0">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className={cn(
          "flex flex-col items-center justify-center gap-1 border-r border-border bg-surface-2 text-muted-foreground hover:bg-muted transition-colors",
          open ? "w-[180px]" : "w-9",
        )}
        aria-label="Toggle document list"
      >
        <Menu className="h-4 w-4" />
        {!open && (
          <span
            className="text-[9px] font-semibold uppercase tracking-wider"
            style={{ writingMode: "vertical-rl" }}
          >
            {files.length} files
          </span>
        )}
        {open && (
          <ul className="w-full px-2 py-2 space-y-1 text-left">
            {files.map((file) => (
              <li key={file.id}>
                <button
                  type="button"
                  onClick={() => {
                    onSelect(file.id);
                    setOpen(false);
                  }}
                  className={cn(
                    "w-full rounded px-2 py-1.5 text-xs truncate text-left hover:bg-background",
                    selectedId === file.id && "bg-primary/10 text-primary font-medium",
                  )}
                >
                  {file.name}
                </button>
              </li>
            ))}
          </ul>
        )}
      </button>
    </div>
  );
}
