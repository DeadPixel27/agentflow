"use client";

import { useParams } from "next/navigation";

import { RunResultsShell } from "@/components/results/run-results-context";

export default function WorkflowRunLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const workflowId = useParams().workflowId as string;

  return (
    <RunResultsShell
      makeRunHref={(runId) => `/workflows/${workflowId}/runs/${runId}`}
    >
      {children}
    </RunResultsShell>
  );
}
