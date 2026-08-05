"use client";

import { ChevronDown, Download, ExternalLink, FileText, Loader2 } from "lucide-react";
import Link from "next/link";
import { Fragment, useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ApiError,
  downloadCsv,
  downloadJson,
  getUploadDocuments,
  inputDocumentUrl,
  type RunResponse,
  type UploadedDocumentSummary,
} from "@/lib/api";
import { cn } from "@/lib/utils";

interface WorkflowRunListProps {
  runs: RunResponse[];
}

function RunDocumentsPanel({ run }: { run: RunResponse }) {
  const [documents, setDocuments] = useState<UploadedDocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getUploadDocuments(run.upload_id)
      .then((res) => {
        if (!cancelled) setDocuments(res.documents);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(
            e instanceof ApiError ? e.message : "Failed to load input documents.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [run.upload_id]);

  const rows = run.result?.rows ?? [];
  const outputFormat = run.result?.format ?? "json";

  return (
    <div className="grid gap-4 sm:grid-cols-2 bg-muted/40 rounded-lg p-4">
      <div className="space-y-2">
        <p className="text-sm font-medium">Input documents</p>
        {loading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Loading…
          </div>
        )}
        {error && <p className="text-sm text-destructive">{error}</p>}
        {!loading && !error && documents.length === 0 && (
          <p className="text-sm text-muted-foreground">No input files found.</p>
        )}
        <ul className="space-y-1.5">
          {documents.map((doc) => (
            <li key={doc.document_id}>
              <a
                href={inputDocumentUrl(run.upload_id, doc.document_id)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
              >
                <FileText className="h-3.5 w-3.5 shrink-0" />
                <span className="truncate">{doc.filename}</span>
                <ExternalLink className="h-3 w-3 shrink-0 opacity-60" />
              </a>
            </li>
          ))}
        </ul>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium">Output</p>
        {run.status !== "completed" || !rows.length ? (
          <p className="text-sm text-muted-foreground">
            {run.status !== "completed"
              ? "Run did not complete successfully."
              : "No output rows for this run."}
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadJson(`run-${run.run_id}.json`, rows)}
            >
              <Download className="mr-1.5 h-3.5 w-3.5" />
              JSON ({rows.length} rows)
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => downloadCsv(`run-${run.run_id}.csv`, rows)}
            >
              <Download className="mr-1.5 h-3.5 w-3.5" />
              CSV ({rows.length} rows)
            </Button>
            <span className="text-xs text-muted-foreground self-center">
              Format: {outputFormat.toUpperCase()}
            </span>
          </div>
        )}
        <Link
          href={`/results/${run.run_id}`}
          className="inline-block text-sm text-primary hover:underline"
        >
          View full results →
        </Link>
      </div>
    </div>
  );
}

export function WorkflowRunList({ runs }: WorkflowRunListProps) {
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);

  if (!runs.length) {
    return (
      <p className="text-sm text-muted-foreground">
        No runs yet. Use the panel above to rerun this workflow.
      </p>
    );
  }

  return (
    <div className="rounded-lg border overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-8" />
            <TableHead>Run</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Documents</TableHead>
            <TableHead className="hidden sm:table-cell">Task</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {runs.map((run) => {
            const expanded = expandedRunId === run.run_id;
            return (
              <Fragment key={run.run_id}>
                <TableRow
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() =>
                    setExpandedRunId(expanded ? null : run.run_id)
                  }
                >
                  <TableCell className="w-8 px-2">
                    <ChevronDown
                      className={cn(
                        "h-4 w-4 text-muted-foreground transition-transform",
                        expanded && "rotate-180",
                      )}
                    />
                  </TableCell>
                  <TableCell>
                    <span className="font-mono text-sm">
                      {run.run_id.slice(0, 8)}…
                    </span>
                  </TableCell>
                  <TableCell>
                <Badge
                  variant={
                    run.status === "completed"
                      ? "default"
                      : run.status === "running"
                        ? "secondary"
                        : "destructive"
                  }
                >
                      {run.status}
                    </Badge>
                  </TableCell>
                  <TableCell>{run.document_ids.length}</TableCell>
                  <TableCell className="hidden sm:table-cell max-w-xs truncate text-muted-foreground">
                    {run.task_description}
                  </TableCell>
                </TableRow>
                {expanded && (
                  <TableRow className="hover:bg-transparent">
                    <TableCell colSpan={5} className="px-4 pb-4">
                      <RunDocumentsPanel run={run} />
                    </TableCell>
                  </TableRow>
                )}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
