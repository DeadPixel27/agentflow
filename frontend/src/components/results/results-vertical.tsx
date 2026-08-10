"use client";

import { AlertCircle, AlertTriangle } from "lucide-react";

import type { FieldConfidence, ValidationWarning } from "@/lib/api";

interface ResultsVerticalListProps {
  rows: Record<string, unknown>[];
  fieldConfidence?: Record<string, FieldConfidence>;
  validationWarnings?: Record<string, ValidationWarning[]>;
}

const META_KEYS = new Set(["document_id", "filename", "flags"]);

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
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
      className={`inline-flex shrink-0 items-center rounded-full border px-1.5 py-0.5 text-[10px] font-medium ${color}`}
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
    <span title={title} aria-label={title} className="inline-flex shrink-0">
      <Icon className={`h-3.5 w-3.5 ${color}`} />
    </span>
  );
}

export function ResultsVerticalList({
  rows,
  fieldConfidence,
  validationWarnings,
}: ResultsVerticalListProps) {
  if (!rows.length) {
    return (
      <p className="text-sm text-muted-foreground text-center py-8">
        No extracted rows for this document.
      </p>
    );
  }

  return (
    <div className="w-full max-w-full space-y-3">
      {rows.map((row, index) => {
        const docId =
          typeof row.document_id === "string" ? row.document_id : undefined;
        const confidence = docId ? fieldConfidence?.[docId] : undefined;
        const warnings = docId ? validationWarnings?.[docId] : undefined;
        const fields = Object.keys(row).filter((k) => !META_KEYS.has(k));
        const filename =
          typeof row.filename === "string" ? row.filename : undefined;

        return (
          <div
            key={docId ? `${docId}-${index}` : index}
            className="w-full max-w-full rounded-lg border border-border bg-card overflow-hidden"
          >
            {(rows.length > 1 || filename) && (
              <div className="px-3 py-2 border-b border-border bg-muted/40 text-[11px] text-muted-foreground truncate">
                {rows.length > 1 ? `Row ${index + 1}` : null}
                {rows.length > 1 && filename ? " · " : null}
                {filename}
              </div>
            )}
            <dl className="divide-y divide-border w-full max-w-full">
              {fields.map((field) => (
                <div
                  key={field}
                  className="grid w-full max-w-full grid-cols-[minmax(0,7.5rem)_minmax(0,1fr)] gap-3 px-3 py-2.5 text-sm"
                >
                  <dt className="text-muted-foreground font-medium truncate">
                    {field}
                  </dt>
                  <dd className="min-w-0 max-w-full flex items-start gap-1.5 overflow-hidden">
                    <span className="min-w-0 flex-1 whitespace-pre-wrap break-words [overflow-wrap:anywhere]">
                      {formatCell(row[field])}
                    </span>
                    <ConfidenceBadge score={confidence?.[field]} />
                    <FieldWarningIcon warnings={warnings} fieldName={field} />
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        );
      })}
    </div>
  );
}
