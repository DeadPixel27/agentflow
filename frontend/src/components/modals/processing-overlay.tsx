"use client";

import { Loader2 } from "lucide-react";

interface ProcessingOverlayProps {
  open: boolean;
  message?: string;
}

export function ProcessingOverlay({
  open,
  message = "Processing your request…",
}: ProcessingOverlayProps) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[400] flex items-center justify-center bg-background/55 backdrop-blur-md"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="flex flex-col items-center gap-3 rounded-lg border border-border bg-card px-8 py-6 shadow-xl">
        <Loader2 className="h-7 w-7 animate-spin text-primary" />
        <p className="text-sm font-medium text-foreground">{message}</p>
      </div>
    </div>
  );
}
