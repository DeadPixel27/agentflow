"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";

import { inputDocumentUrl } from "@/lib/api";

function ExtractionMethodBadge({ method }: { method?: string }) {
  if (!method) return null;

  const config: Record<string, { label: string; color: string }> = {
    pymupdf: { label: "Digital PDF", color: "bg-blue-100 text-blue-700" },
    tesseract: { label: "OCR (Tesseract)", color: "bg-slate-100 text-slate-700" },
    rapidocr: { label: "OCR (RapidOCR)", color: "bg-indigo-100 text-indigo-700" },
    docling: { label: "Layout-Aware", color: "bg-purple-100 text-purple-700" },
  };

  const { label, color } = config[method] ?? {
    label: method,
    color: "bg-slate-100 text-slate-600",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${color}`}
    >
      {label}
    </span>
  );
}

interface DocumentTabPanelProps {
  uploadId: string;
  documentId: string;
  filename: string;
  extractionMethod?: string;
}

export function DocumentTabPanel({
  uploadId,
  documentId,
  filename,
  extractionMethod,
}: DocumentTabPanelProps) {
  const [page, setPage] = useState(1);
  const totalPages = 2;
  const url = inputDocumentUrl(uploadId, documentId);

  return (
    <div className="flex flex-1 flex-col min-h-0 bg-[#F5F5F4]">
      <div className="flex-1 overflow-auto p-6 flex justify-center">
        <div className="w-full max-w-[480px] rounded-lg bg-white shadow-md p-8 space-y-4">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-xs text-muted-foreground uppercase tracking-wide truncate">
              {filename}
            </p>
            <ExtractionMethodBadge method={extractionMethod} />
          </div>
          <div className="space-y-3 text-sm leading-relaxed text-foreground/90">
            <p>
              Sample extracted preview. Fields like{" "}
              <span className="pdf-highlight">Vendor Name</span> and{" "}
              <span className="pdf-highlight">Invoice Total</span> would be
              highlighted on the real document.
            </p>
            <p className="text-muted-foreground text-xs">
              Full document preview:
            </p>
            <iframe
              src={url}
              title={filename}
              className="w-full h-[360px] rounded border border-border"
            />
          </div>
        </div>
      </div>
      <div className="shrink-0 flex items-center justify-center gap-3 py-2 border-t border-border bg-background text-sm">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          className="p-1 rounded hover:bg-muted disabled:opacity-40"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-xs text-muted-foreground tabular-nums">
          {page}/{totalPages}
        </span>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          className="p-1 rounded hover:bg-muted disabled:opacity-40"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
