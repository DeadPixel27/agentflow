"use client";

import { AlertCircle, AlertTriangle, CheckCircle2, ChevronDown, Circle, Loader2, SkipForward, XCircle } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import type {
  FieldConfidence,
  PlannedStep,
  StepRun,
  ValidationWarning,
} from "@/lib/api";
import { cn } from "@/lib/utils";

interface StepStatusListProps {
  steps: StepRun[];
  plannedSteps?: PlannedStep[];
  showProgress?: boolean;
}

function StepIcon({ status }: { status: string }) {
  if (status === "completed") {
    return <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />;
  }
  if (status === "running") {
    return <Loader2 className="h-4 w-4 animate-spin text-primary shrink-0" />;
  }
  if (status === "failed") {
    return <XCircle className="h-4 w-4 text-destructive shrink-0" />;
  }
  if (status === "skipped") {
    return <SkipForward className="h-4 w-4 text-muted-foreground shrink-0" />;
  }
  return <Circle className="h-4 w-4 text-muted-foreground/40 shrink-0" />;
}

function badgeVariant(status: string): "default" | "destructive" | "secondary" {
  if (status === "completed") return "default";
  if (status === "failed") return "destructive";
  if (status === "running") return "secondary";
  return "secondary";
}

function formatJson(value: unknown): string {
  if (value === null || value === undefined) return "—";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function hasOutput(output: Record<string, unknown> | undefined): boolean {
  return Boolean(output && Object.keys(output).length > 0);
}

interface StepCardProps {
  step: StepRun;
  planned?: PlannedStep;
  expanded: boolean;
  onToggle: () => void;
}

function StepCard({ step, planned, expanded, onToggle }: StepCardProps) {
  const canExpand = Boolean(
    planned?.reason ||
      (planned?.config && Object.keys(planned.config).length > 0) ||
      hasOutput(step.output) ||
      step.error_message,
  );

  return (
    <div
      className={cn(
        "rounded-lg border transition-colors",
        step.status === "running" && "border-primary/50 bg-primary/5",
      )}
    >
      <button
        type="button"
        onClick={canExpand ? onToggle : undefined}
        className={cn(
          "flex w-full items-center justify-between px-4 py-3 text-left",
          canExpand && "hover:bg-muted/40 cursor-pointer",
          !canExpand && "cursor-default",
        )}
        aria-expanded={canExpand ? expanded : undefined}
      >
        <div className="flex items-start gap-3 min-w-0">
          <StepIcon status={step.status} />
          <div className="min-w-0">
            <p className="font-medium text-sm">
              Step {step.step_order}: {step.agent_type}
            </p>
            {planned?.reason && !expanded && (
              <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                {planned.reason}
              </p>
            )}
            {step.error_message && !expanded && (
              <p className="text-sm text-destructive mt-1 line-clamp-2">
                {step.error_message}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-2">
          <Badge variant={badgeVariant(step.status)}>{step.status}</Badge>
          {canExpand && (
            <ChevronDown
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform",
                expanded && "rotate-180",
              )}
            />
          )}
        </div>
      </button>

      {expanded && canExpand && (
        <div className="border-t px-4 py-3 space-y-3 bg-muted/20">
          {planned?.reason && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Why this step
              </p>
              <p className="text-sm">{planned.reason}</p>
            </div>
          )}

          {planned?.config && Object.keys(planned.config).length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Config
              </p>
              <pre className="text-xs bg-background rounded-md border p-3 overflow-x-auto max-h-40">
                {formatJson(planned.config)}
              </pre>
            </div>
          )}

          {hasOutput(step.output) && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Output
              </p>
              <pre className="text-xs bg-background rounded-md border p-3 overflow-x-auto max-h-60">
                {formatJson(step.output)}
              </pre>
            </div>
          )}

          {step.error_message && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-destructive uppercase tracking-wide">
                Error
              </p>
              <p className="text-sm text-destructive">{step.error_message}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function StepStatusList({
  steps,
  plannedSteps = [],
  showProgress = false,
}: StepStatusListProps) {
  const completed = steps.filter((s) => s.status === "completed").length;
  const total = steps.length;
  const progress = total > 0 ? Math.round((completed / total) * 100) : 0;
  const runningStep = steps.find((s) => s.status === "running");

  const plannedByOrder = new Map(
    plannedSteps.map((planned) => [planned.step_order, planned]),
  );

  const [expandedOrders, setExpandedOrders] = useState<Set<number>>(new Set());

  const runningStepOrder = runningStep?.step_order;

  useEffect(() => {
    if (runningStepOrder === undefined) return;
    setExpandedOrders((prev) => {
      const next = new Set(prev);
      next.add(runningStepOrder);
      return next;
    });
  }, [runningStepOrder]);

  function toggleStep(stepOrder: number) {
    setExpandedOrders((prev) => {
      const next = new Set(prev);
      if (next.has(stepOrder)) next.delete(stepOrder);
      else next.add(stepOrder);
      return next;
    });
  }

  return (
    <div className="space-y-4">
      {showProgress && total > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">
              {runningStep
                ? `Running step ${runningStep.step_order} of ${total}…`
                : completed === total
                  ? "Pipeline complete"
                  : "Preparing pipeline…"}
            </span>
            <span className="text-muted-foreground tabular-nums">{progress}%</span>
          </div>
          <Progress value={progress} />
        </div>
      )}

      <div className="space-y-2">
        {steps.map((step) => (
          <StepCard
            key={step.step_order}
            step={step}
            planned={plannedByOrder.get(step.step_order)}
            expanded={expandedOrders.has(step.step_order)}
            onToggle={() => toggleStep(step.step_order)}
          />
        ))}
      </div>
    </div>
  );
}

interface ResultsTableProps {
  rows: Record<string, unknown>[];
  fieldConfidence?: Record<string, FieldConfidence>;
  validationWarnings?: Record<string, ValidationWarning[]>;
}

function ConfidenceBadge({ score }: { score?: number }) {
  if (score === undefined || score === null) return null;

  const pct = Math.round(score * 100);
  let color: string;

  if (score >= 0.9) {
    color = "bg-emerald-100 text-emerald-700 border-emerald-200";
  } else if (score >= 0.7) {
    color = "bg-amber-100 text-amber-700 border-amber-200";
  } else {
    color = "bg-red-100 text-red-700 border-red-200";
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-medium ${color}`}
      title={`Confidence: ${pct}%`}
    >
      {pct}%
    </span>
  );
}

function FieldWarningIcon({
  warnings,
  fieldName,
}: {
  warnings?: ValidationWarning[];
  fieldName: string;
}) {
  if (!warnings?.length) return null;
  const fieldWarnings = warnings.filter((w) => w.field === fieldName);
  if (fieldWarnings.length === 0) return null;

  const isError = fieldWarnings.some((w) => w.severity === "error");
  const Icon = isError ? AlertCircle : AlertTriangle;
  const color = isError ? "text-red-500" : "text-amber-500";
  const title = fieldWarnings.map((w) => w.message).join(" · ");

  return (
    <span title={title} aria-label={title} className="inline-flex">
      <Icon className={`h-3.5 w-3.5 ${color} ml-1 shrink-0`} />
    </span>
  );
}

export function ResultsTable({
  rows,
  fieldConfidence,
  validationWarnings,
}: ResultsTableProps) {
  if (!rows.length) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        No extracted rows yet.
      </p>
    );
  }

  const columns = Object.keys(rows[0]).filter(
    (k) => k !== "flags" && k !== "document_id",
  );

  const columnLabel = (col: string) => (col === "filename" ? "Document" : col);

  return (
    <div className="rounded-lg border overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/50">
            {columns.map((col) => (
              <th
                key={col}
                className="px-4 py-2 text-left font-medium text-muted-foreground"
              >
                {columnLabel(col)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const docId =
              typeof row.document_id === "string" ? row.document_id : undefined;
            const confidence = docId ? fieldConfidence?.[docId] : undefined;
            const warnings = docId ? validationWarnings?.[docId] : undefined;

            return (
              <tr key={i} className="border-b last:border-0">
                {columns.map((col) => (
                  <td key={col} className="px-4 py-2 max-w-xs">
                    <span className="inline-flex items-center gap-1.5 max-w-full">
                      <span className="truncate">{formatCell(row[col])}</span>
                      {col !== "filename" && (
                        <>
                          <ConfidenceBadge score={confidence?.[col]} />
                          <FieldWarningIcon
                            warnings={warnings}
                            fieldName={col}
                          />
                        </>
                      )}
                    </span>
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function RunSummaryStats({
  documentCount,
  rowCount,
  stepCount,
  flagCount,
}: {
  documentCount: number;
  rowCount: number;
  stepCount: number;
  flagCount: number;
}) {
  const stats = [
    { label: "Documents", value: documentCount },
    { label: "Rows extracted", value: rowCount },
    { label: "Pipeline steps", value: stepCount },
    { label: "Flags raised", value: flagCount },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="rounded-lg border bg-background px-4 py-3 text-center"
        >
          <p className="text-2xl font-semibold tabular-nums">{stat.value}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{stat.label}</p>
        </div>
      ))}
    </div>
  );
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
