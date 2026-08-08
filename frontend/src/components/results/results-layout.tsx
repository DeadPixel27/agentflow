"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { type SaveAction, ExportBar } from "@/components/export-bar";
import { NavBar } from "@/components/nav-bar";
import { RefineChatPanel } from "@/components/refine-chat";
import { DocumentTabPanel } from "@/components/results/document-tab";
import { DocsPanel } from "@/components/results/docs-panel";
import { ResultsTabPanel } from "@/components/results/results-tab";
import { TabSwitcher, type ResultsTab } from "@/components/results/tab-switcher";
import { StepStatusList } from "@/components/run-display";
import { TopBar } from "@/components/top-bar";
import { getUploadDocuments, type RunResponse } from "@/lib/api";

interface ResultsLayoutProps {
  run: RunResponse;
  isRunning: boolean;
  backHref: string;
  backLabel?: string;
  title?: string;
  saveAction?: SaveAction;
  workflowId?: string;
  versionLabel?: string;
  defaultEmail?: string;
  defaultSheetsUrl?: string;
  onRefined: (newRunId: string) => void;
  onWorkflowSaved?: (workflowId: string) => void;
}

export function ResultsLayout({
  run,
  isRunning,
  backHref,
  backLabel,
  title = "Pipeline Results",
  saveAction = "workflow",
  workflowId,
  versionLabel,
  defaultEmail,
  defaultSheetsUrl,
  onRefined,
  onWorkflowSaved,
}: ResultsLayoutProps) {
  const [activeTab, setActiveTab] = useState<ResultsTab>("results");
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [docNames, setDocNames] = useState<Record<string, string>>({});

  const rows = run.result?.rows ?? [];
  const flagCount = rows.reduce((count, row) => {
    const flags = row.flags;
    if (Array.isArray(flags)) return count + flags.length;
    return count;
  }, 0);

  useEffect(() => {
    if (!run.upload_id) return;
    getUploadDocuments(run.upload_id)
      .then((res) => {
        const map: Record<string, string> = {};
        for (const doc of res.documents) {
          map[doc.document_id] = doc.filename;
        }
        setDocNames(map);
        if (res.documents[0] && !selectedDocId) {
          setSelectedDocId(res.documents[0].document_id);
        }
      })
      .catch(() => {
        /* optional */
      });
  }, [run.upload_id, selectedDocId]);

  const files = useMemo(
    () =>
      run.document_ids.map((id) => ({
        id,
        name: docNames[id] ?? id.slice(0, 8),
      })),
    [run.document_ids, docNames],
  );

  const statusBadge =
    run.status === "completed" ? (
      <span className="v2-badge-success">{run.status}</span>
    ) : run.status === "running" ? (
      <span className="v2-badge-muted">{run.status}</span>
    ) : (
      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold bg-destructive/10 text-destructive">
        {run.status}
      </span>
    );

  const meta = [
    run.task_description,
    `${run.document_ids.length} documents`,
    run.run_id.slice(0, 8),
  ]
    .filter(Boolean)
    .join(" · ");

  const showResults = !isRunning && run.status === "completed";

  return (
    <div className="v2-page">
      <NavBar />
      <TopBar
        backHref={backHref}
        backLabel={backLabel}
        title={title}
        meta={meta}
        badge={
          <>
            {statusBadge}
            {versionLabel && (
              <span className="v2-badge-success ml-1">{versionLabel}</span>
            )}
          </>
        }
      />

      {showResults && (
        <ExportBar
          runId={run.run_id}
          rows={rows}
          saveAction={saveAction}
          workflowId={workflowId ?? run.workflow_id ?? undefined}
          defaultEmail={defaultEmail}
          defaultSheetsUrl={defaultSheetsUrl}
          onWorkflowSaved={onWorkflowSaved}
        />
      )}

      <div className="flex flex-1 min-h-0">
        {showResults && (
          <DocsPanel
            files={files}
            selectedId={selectedDocId}
            onSelect={(id) => {
              setSelectedDocId(id);
              setActiveTab("document");
            }}
          />
        )}

        <div className="flex flex-1 flex-col min-w-0 min-h-0">
          {isRunning || run.status !== "completed" ? (
            <div className="flex-1 overflow-auto p-6 space-y-4">
              {isRunning && (
                <div className="flex items-center gap-2 text-muted-foreground text-sm">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Pipeline running…
                </div>
              )}
              <StepStatusList
                steps={run.steps}
                plannedSteps={run.planned_steps}
                showProgress={isRunning}
              />
              {run.status === "failed" && run.error_message && (
                <p className="text-sm text-destructive">{run.error_message}</p>
              )}
            </div>
          ) : (
            <>
              <TabSwitcher active={activeTab} onChange={setActiveTab} />
              {activeTab === "results" ? (
                <ResultsTabPanel rows={rows} flagCount={flagCount} />
              ) : selectedDocId ? (
                <DocumentTabPanel
                  uploadId={run.upload_id}
                  documentId={selectedDocId}
                  filename={docNames[selectedDocId] ?? "Document"}
                />
              ) : (
                <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
                  Select a document from the strip.
                </div>
              )}
            </>
          )}
        </div>

        {showResults && (
          <RefineChatPanel
            runId={run.run_id}
            disabled={isRunning}
            documentCount={run.document_ids.length}
            versionLabel={versionLabel}
            variant="panel"
            onRefined={(newRunId) => onRefined(newRunId)}
          />
        )}
      </div>
    </div>
  );
}
