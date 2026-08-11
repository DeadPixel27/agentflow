"use client";

import { RunResultsShell } from "@/components/results/run-results-context";

export default function ResultsRunLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <RunResultsShell makeRunHref={(runId) => `/results/${runId}`}>
      {children}
    </RunResultsShell>
  );
}
