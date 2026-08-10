"use client";

import { Download } from "lucide-react";
import { useState } from "react";

import { EmailModal } from "@/components/modals/email-modal";
import { SaveVersionModal } from "@/components/modals/save-version-modal";
import { SaveWorkflowModal } from "@/components/modals/save-workflow-modal";
import { SheetsModal } from "@/components/modals/sheets-modal";
import { Button } from "@/components/ui/button";
import { downloadCsv, downloadJson } from "@/lib/api";

export type SaveAction = "workflow" | "version" | "none";

interface ExportBarProps {
  runId: string;
  rows: Record<string, unknown>[];
  saveAction?: SaveAction;
  workflowId?: string;
  defaultEmail?: string;
  defaultSheetsUrl?: string;
  onWorkflowSaved?: (workflowId: string) => void;
  onVersionSaved?: () => void;
}

export function ExportBar({
  runId,
  rows,
  saveAction = "workflow",
  workflowId,
  defaultEmail,
  defaultSheetsUrl,
  onWorkflowSaved,
  onVersionSaved,
}: ExportBarProps) {
  const [showSave, setShowSave] = useState(false);
  const [showVersion, setShowVersion] = useState(false);
  const [showEmail, setShowEmail] = useState(false);
  const [showSheets, setShowSheets] = useState(false);

  const hasRows = rows.length > 0;

  return (
    <>
      <div className="shrink-0 flex flex-wrap items-center gap-2 border-b border-border bg-surface-2 px-4 py-2">
        <Button
          variant="outline"
          size="sm"
          disabled={!hasRows}
          onClick={() => downloadCsv(`run-${runId}.csv`, rows)}
        >
          <Download className="mr-1.5 h-3.5 w-3.5" />
          CSV
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={!hasRows}
          onClick={() => downloadJson(`run-${runId}.json`, rows)}
        >
          <Download className="mr-1.5 h-3.5 w-3.5" />
          JSON
        </Button>
        <Button variant="outline" size="sm" onClick={() => setShowEmail(true)}>
          Email
        </Button>
        <Button variant="outline" size="sm" onClick={() => setShowSheets(true)}>
          Sheets
        </Button>
        {saveAction === "workflow" && (
          <Button size="sm" className="ml-auto" onClick={() => setShowSave(true)}>
            Save as Workflow
          </Button>
        )}
        {saveAction === "version" && workflowId && (
          <Button
            size="sm"
            className="ml-auto"
            onClick={() => setShowVersion(true)}
          >
            Save as New Version
          </Button>
        )}
      </div>

      <SaveWorkflowModal
        open={showSave}
        onClose={() => setShowSave(false)}
        runId={runId}
        onSaved={(id) => {
          setShowSave(false);
          onWorkflowSaved?.(id);
        }}
      />
      {workflowId && (
        <SaveVersionModal
          open={showVersion}
          onClose={() => setShowVersion(false)}
          workflowId={workflowId}
          runId={runId}
          onSaved={() => {
            setShowVersion(false);
            onVersionSaved?.();
          }}
        />
      )}
      <EmailModal
        open={showEmail}
        onClose={() => setShowEmail(false)}
        runId={runId}
        defaultTo={defaultEmail}
      />
      <SheetsModal
        open={showSheets}
        onClose={() => setShowSheets(false)}
        runId={runId}
        defaultUrl={defaultSheetsUrl}
      />
    </>
  );
}
