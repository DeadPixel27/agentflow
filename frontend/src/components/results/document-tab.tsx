"use client";

import { ExternalLink, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

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

function isImageFile(filename: string, fileType?: string): boolean {
  const type = (fileType ?? "").toLowerCase();
  if (type.startsWith("image/")) return true;
  return /\.(png|jpe?g|gif|webp|bmp|tiff?)$/i.test(filename);
}

interface DocumentTabPanelProps {
  uploadId: string;
  documentId: string;
  filename: string;
  fileType?: string;
  extractionMethod?: string;
  className?: string;
}

export function DocumentTabPanel({
  uploadId,
  documentId,
  filename,
  fileType,
  extractionMethod,
  className,
}: DocumentTabPanelProps) {
  const [ready, setReady] = useState(false);
  const url = useMemo(
    () => inputDocumentUrl(uploadId, documentId),
    [uploadId, documentId],
  );
  const image = isImageFile(filename, fileType);

  useEffect(() => {
    setReady(false);
    const timer = window.setTimeout(() => setReady(true), 0);
    return () => window.clearTimeout(timer);
  }, [documentId, url]);

  return (
    <div className={`flex flex-1 flex-col min-h-0 bg-[#F5F5F4] ${className ?? ""}`}>
      <div className="shrink-0 flex items-center gap-2 flex-wrap px-4 py-2 border-b border-border bg-background">
        <p className="text-xs text-muted-foreground uppercase tracking-wide truncate flex-1 min-w-0">
          {filename}
        </p>
        <ExtractionMethodBadge method={extractionMethod} />
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
        >
          <ExternalLink className="h-3 w-3" />
          Open
        </a>
      </div>

      <div className="flex-1 min-h-0 overflow-hidden p-3">
        {!ready ? (
          <div className="flex h-full items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading document…
          </div>
        ) : image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={url}
            alt={filename}
            className="h-full w-full object-contain rounded border border-border bg-white"
          />
        ) : (
          <iframe
            key={url}
            src={url}
            title={filename}
            className="h-full w-full rounded border border-border bg-white"
          />
        )}
      </div>
    </div>
  );
}
