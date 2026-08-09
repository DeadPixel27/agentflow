"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";

import { ExportBar } from "@/components/export-bar";
import { DocumentTabPanel } from "@/components/results/document-tab";
import { DocsPanel } from "@/components/results/docs-panel";
import { ResultsTabPanel } from "@/components/results/results-tab";
import { useRunResultsContext } from "@/components/results/run-results-context";
import { TabSwitcher, type ResultsTab } from "@/components/results/tab-switcher";
import { StepStatusList } from "@/components/run-display";
import { TopBar } from "@/components/top-bar";
import { getUploadDocuments, type RunResponse } from "@/lib/api";

function PipelinePanel({
  isRunning,
  title = "Pipeline",
}: {
  isRunning: boolean;
  title?: string;
}) {
  const { runState } = useRunResultsContext();
  const run = runState.run;
  if (!run) return null;

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

function inferPipelineExtractionMethod(
  run?: RunResponse | null,
): string | undefined {
  if (!run?.steps?.length) return undefined;
  const completed = run.steps.filter((s) => s.status === "completed");
  if (completed.some((s) => s.agent_type === "processor.ocr")) {
    return "rapidocr";
  }
  if (completed.some((s) => s.agent_type === "processor.text_extract")) {
    return "pymupdf";
  }
  return undefined;
}

interface RunResultsFrameProps {
  refinePanel: ReactNode;
}

export function RunResultsFrame({ refinePanel }: RunResultsFrameProps) {
  const { runState, pageConfig, setHasCompletedResults, setRefineDisabled } =
    useRunResultsContext();
  const { run, isRunning, loading, error } = runState;

  const [activeTab, setActiveTab] = useState<ResultsTab>("results");
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [docNames, setDocNames] = useState<Record<string, string>>({});
  const [docMethods, setDocMethods] = useState<Record<string, string>>({});
  const [refineUnlocked, setRefineUnlocked] = useState(false);
  const [lastCompletedRun, setLastCompletedRun] = useState(
    run?.status === "completed" ? run : null,
  );

  useEffect(() => {
    if (run?.status === "completed") {
      setRefineUnlocked(true);
      setLastCompletedRun(run);
    }
  }, [run]);

  useEffect(() => {
    setRefineDisabled(isRunning);
  }, [isRunning, setRefineDisabled]);

  const displayRun =
    run?.status === "completed" ? run : (lastCompletedRun ?? run);
  const rows = displayRun?.result?.rows ?? [];
  const flagCount = rows.reduce((count, row) => {
    const flags = row.flags;
    if (Array.isArray(flags)) return count + flags.length;
    return count;
  }, 0);

  const hasCompletedResults =
    refineUnlocked && displayRun?.status === "completed";
  const isRerunning = isRunning && hasCompletedResults;
  const showPipelineProgress =
    !hasCompletedResults &&
    Boolean(run) &&
    (isRunning || run!.status !== "completed");

  useEffect(() => {
    setHasCompletedResults(hasCompletedResults);
  }, [hasCompletedResults, setHasCompletedResults]);

  const uploadId = run?.upload_id || displayRun?.upload_id;

  useEffect(() => {
    if (!uploadId) return;
    getUploadDocuments(uploadId)
      .then((res) => {
        const map: Record<string, string> = {};
        const methods: Record<string, string> = {};
        for (const doc of res.documents) {
          map[doc.document_id] = doc.filename;
          if (doc.extraction_method) {
            methods[doc.document_id] = doc.extraction_method;
          }
        }
        setDocNames(map);
        setDocMethods(methods);
        if (res.documents[0] && !selectedDocId) {
          setSelectedDocId(res.documents[0].document_id);
        }
      })
      .catch(() => {
        /* optional */
      });
  }, [uploadId, selectedDocId]);

  const docSourceRun = hasCompletedResults ? displayRun : run;
  const fallbackMethod = inferPipelineExtractionMethod(displayRun ?? run);
  const validationWarnings = displayRun?.result?.validation_warnings;
  const files = useMemo(
    () =>
      (docSourceRun?.document_ids ?? []).map((id) => ({
        id,
        name: docNames[id] ?? id.slice(0, 8),
        warningCount: validationWarnings?.[id]?.length ?? 0,
      })),
    [docSourceRun?.document_ids, docNames, validationWarnings],
  );
  const totalWarnings = useMemo(
    () =>
      Object.values(validationWarnings ?? {}).reduce(
        (sum, list) => sum + list.length,
        0,
      ),
    [validationWarnings],
  );

  const showDocsPanel = files.length > 0;

  const statusBadge =
    displayRun?.status === "completed" ? (
      <span className="v2-badge-success">{displayRun.status}</span>
    ) : displayRun?.status === "running" ? (
      <span className="v2-badge-muted">{displayRun.status}</span>
    ) : displayRun ? (
      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold bg-destructive/10 text-destructive">
        {displayRun.status}
      </span>
    ) : null;

  const meta = displayRun
    ? [
        displayRun.task_description,
        `${displayRun.document_ids.length} documents`,
        displayRun.run_id.slice(0, 8),
      ]
        .filter(Boolean)
        .join(" · ")
    : undefined;

  if (loading && !run) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error && !run) {
    return (
      <div className="flex flex-1 items-center justify-center p-4">
        <p className="text-destructive" role="alert">
          {error}
        </p>
      </div>
    );
  }

  if (!run || !displayRun) return null;

  return (
    <>
      <TopBar
        backHref={pageConfig.backHref}
        backLabel={pageConfig.backLabel}
        title={pageConfig.title ?? "Pipeline Results"}
        meta={meta}
        badge={
          <>
            {statusBadge}
            {pageConfig.versionLabel && (
              <span className="v2-badge-success ml-1">
                {pageConfig.versionLabel}
              </span>
            )}
          </>
        }
      />

      {hasCompletedResults && (
        <ExportBar
          runId={displayRun.run_id}
          rows={rows}
          saveAction={pageConfig.saveAction ?? "workflow"}
          workflowId={pageConfig.workflowId ?? displayRun.workflow_id ?? undefined}
          defaultEmail={pageConfig.defaultEmail}
          defaultSheetsUrl={pageConfig.defaultSheetsUrl}
          onWorkflowSaved={pageConfig.onWorkflowSaved}
          onVersionSaved={pageConfig.onVersionSaved}
        />
      )}

      <div className="flex flex-1 min-h-0">
        {showDocsPanel && (
          <DocsPanel
            files={files}
            selectedId={selectedDocId}
            totalWarnings={totalWarnings}
            onSelect={(id) => {
              setSelectedDocId(id);
              if (!showPipelineProgress) {
                setActiveTab("document");
              }
            }}
          />
        )}

        <div className="flex flex-1 flex-col min-w-0 min-h-0">
          {isRerunning && (
            <div className="shrink-0 flex items-center gap-2 border-b border-primary/20 bg-primary/5 px-4 py-2 text-xs text-primary">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span>Re-running extraction with your refinements...</span>
            </div>
          )}
          {showPipelineProgress ? (
            <PipelinePanel
              isRunning={isRunning}
              title={hasCompletedResults ? "Re-running" : "Pipeline"}
            />
          ) : (
            <>
              <TabSwitcher active={activeTab} onChange={setActiveTab} />
              {activeTab === "results" ? (
                <ResultsTabPanel
                  rows={rows}
                  flagCount={flagCount}
                  isUpdating={isRerunning}
                  fieldConfidence={displayRun?.result?.field_confidence}
                  validationWarnings={displayRun?.result?.validation_warnings}
                />
              ) : selectedDocId ? (
                <DocumentTabPanel
                  uploadId={displayRun.upload_id}
                  documentId={selectedDocId}
                  filename={docNames[selectedDocId] ?? "Document"}
                  extractionMethod={
                    docMethods[selectedDocId] ?? fallbackMethod
                  }
                />
              ) : (
                <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
                  Select a document from the strip.
                </div>
              )}
            </>
          )}
        </div>
        {refinePanel}
      </div>
    </>
  );
}
