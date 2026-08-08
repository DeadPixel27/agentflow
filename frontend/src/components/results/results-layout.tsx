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
  refineRunId: string;
  chatSessionKey: string;
  onRefined: (newRunId: string) => void;
  onWorkflowSaved?: (workflowId: string) => void;
  onVersionSaved?: () => void;
}

function RefinePlaceholder({ running }: { running: boolean }) {
  return (
    <aside className="w-[340px] shrink-0 flex flex-col border-l border-border bg-card min-h-0">
      <div className="shrink-0 p-4 border-b border-border space-y-2">
        <h2 className="font-serif text-base font-semibold">Refine</h2>
        <p className="text-xs text-muted-foreground">
          {running
            ? "Chat refinement unlocks when extraction finishes."
            : "Describe what to change once results are ready."}
        </p>
      </div>
      <div className="flex-1 flex items-center justify-center p-6 text-center">
        {running && (
          <div className="flex flex-col items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>Pipeline running…</span>
          </div>
        )}
      </div>
    </aside>
  );
}

function PipelinePanel({
  run,
  isRunning,
  title = "Pipeline",
}: {
  run: RunResponse;
  isRunning: boolean;
  title?: string;
}) {
  return (
    <>
      <div className="shrink-0 flex gap-4 border-b border-border px-4">
        <span className="pb-2 text-sm font-medium border-b-2 border-primary text-primary -mb-px">
          {title}
        </span>
      </div>
      <div className="flex-1 overflow-auto p-4 space-y-4 min-h-0">
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
    </>
  );
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
  refineRunId,
  chatSessionKey,
  onRefined,
  onWorkflowSaved,
  onVersionSaved,
}: ResultsLayoutProps) {
  const [activeTab, setActiveTab] = useState<ResultsTab>("results");
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [docNames, setDocNames] = useState<Record<string, string>>({});
  const [refineUnlocked, setRefineUnlocked] = useState(false);
  const [lastCompletedRun, setLastCompletedRun] = useState<RunResponse | null>(
    null,
  );

  useEffect(() => {
    if (run.status === "completed") {
      setRefineUnlocked(true);
      setLastCompletedRun(run);
    }
  }, [run]);

  const displayRun =
    run.status === "completed" ? run : (lastCompletedRun ?? run);
  const rows = displayRun.result?.rows ?? [];
  const flagCount = rows.reduce((count, row) => {
    const flags = row.flags;
    if (Array.isArray(flags)) return count + flags.length;
    return count;
  }, 0);

  const hasCompletedResults =
    refineUnlocked && displayRun.status === "completed";
  const showPipelineProgress =
    isRunning || (!hasCompletedResults && run.status !== "completed");
  const showRerunBanner = isRunning && hasCompletedResults;

  const uploadId = run.upload_id || displayRun.upload_id;

  useEffect(() => {
    if (!uploadId) return;
    getUploadDocuments(uploadId)
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
  }, [uploadId, selectedDocId]);

  const docSourceRun = hasCompletedResults ? displayRun : run;
  const files = useMemo(
    () =>
      docSourceRun.document_ids.map((id) => ({
        id,
        name: docNames[id] ?? id.slice(0, 8),
      })),
    [docSourceRun.document_ids, docNames],
  );

  const showDocsPanel = files.length > 0;

  const statusBadge = showRerunBanner ? (
    <span className="v2-badge-muted">re-running</span>
  ) : run.status === "completed" ? (
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

      {hasCompletedResults && (
        <ExportBar
          runId={displayRun.run_id}
          rows={rows}
          saveAction={saveAction}
          workflowId={workflowId ?? displayRun.workflow_id ?? undefined}
          defaultEmail={defaultEmail}
          defaultSheetsUrl={defaultSheetsUrl}
          onWorkflowSaved={onWorkflowSaved}
          onVersionSaved={onVersionSaved}
        />
      )}

      <div className="flex flex-1 min-h-0">
        {showDocsPanel && (
          <DocsPanel
            files={files}
            selectedId={selectedDocId}
            onSelect={(id) => {
              setSelectedDocId(id);
              if (!showPipelineProgress) {
                setActiveTab("document");
              }
            }}
          />
        )}

        <div className="flex flex-1 flex-col min-w-0 min-h-0">
          {showRerunBanner && (
            <div className="shrink-0 flex items-center gap-2 border-b border-border bg-surface-2 px-4 py-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Re-running extraction with your refinements…
            </div>
          )}

          {showPipelineProgress ? (
            <PipelinePanel
              run={run}
              isRunning={isRunning}
              title={hasCompletedResults ? "Re-running" : "Pipeline"}
            />
          ) : (
            <>
              <TabSwitcher active={activeTab} onChange={setActiveTab} />
              {activeTab === "results" ? (
                <ResultsTabPanel rows={rows} flagCount={flagCount} />
              ) : selectedDocId ? (
                <DocumentTabPanel
                  uploadId={displayRun.upload_id}
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

        {hasCompletedResults ? (
          <RefineChatPanel
            runId={refineRunId}
            chatSessionKey={chatSessionKey}
            disabled={isRunning}
            saveAction={saveAction}
            variant="panel"
            onRefined={(newRunId) => onRefined(newRunId)}
          />
        ) : (
          <RefinePlaceholder running={isRunning} />
        )}
      </div>
    </div>
  );
}
