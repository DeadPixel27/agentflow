"use client";

import { Upload } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import {
  MAX_FILES_PER_UPLOAD,
  MAX_PAGES_PER_FILE,
  MAX_UPLOAD_SIZE_BYTES,
  MAX_UPLOAD_SIZE_MB,
  countPdfPages,
  formatFileSize,
} from "@/lib/upload-limits";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
  disabled?: boolean;
}

export function UploadZone({ files, onFilesChange, disabled }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);

  const addFiles = useCallback(
    async (incoming: FileList | File[]) => {
      const accepted: File[] = [];

      for (const file of Array.from(incoming)) {
        const ext = file.name.toLowerCase();
        if (![".pdf", ".png", ".jpg", ".jpeg"].some((e) => ext.endsWith(e))) {
          continue;
        }
        if (file.size > MAX_UPLOAD_SIZE_BYTES) {
          toast.error(
            `"${file.name}" is too large (${formatFileSize(file.size)}). Max ${MAX_UPLOAD_SIZE_MB} MB per file.`,
          );
          continue;
        }

        const pages = await countPdfPages(file);
        if (pages != null && pages > MAX_PAGES_PER_FILE) {
          toast.error(
            `"${file.name}" has ${pages} pages. Max ${MAX_PAGES_PER_FILE} pages per file.`,
          );
          continue;
        }

        accepted.push(file);
      }

      if (!accepted.length) return;

      const merged = [...files, ...accepted].slice(0, MAX_FILES_PER_UPLOAD);
      if (files.length + accepted.length > MAX_FILES_PER_UPLOAD) {
        toast.error(`Maximum ${MAX_FILES_PER_UPLOAD} files per upload.`);
      }
      onFilesChange(merged);
    },
    [files, onFilesChange],
  );

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!disabled) void addFiles(e.dataTransfer.files);
        }}
        className={cn(
          "flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition-colors",
          dragging ? "border-primary bg-primary/5" : "border-muted-foreground/25",
          disabled && "opacity-50 pointer-events-none",
        )}
      >
        <Upload className="h-8 w-8 text-muted-foreground" />
        <div>
          <p className="font-medium">Drop PDFs or images here</p>
          <p className="text-sm text-muted-foreground mt-1">
            Up to {MAX_FILES_PER_UPLOAD} files — PDF, PNG, JPG — max{" "}
            {MAX_UPLOAD_SIZE_MB} MB · {MAX_PAGES_PER_FILE} pages each
          </p>
        </div>
        <label className="cursor-pointer text-sm font-medium text-primary underline-offset-4 hover:underline">
          Browse files
          <input
            type="file"
            className="sr-only"
            multiple
            accept=".pdf,.png,.jpg,.jpeg"
            disabled={disabled}
            onChange={(e) => e.target.files && void addFiles(e.target.files)}
          />
        </label>
      </div>

      {files.length > 0 && (
        <ul className="text-sm space-y-1">
          {files.map((f, i) => (
            <li
              key={`${f.name}-${i}`}
              className="flex items-center justify-between rounded-md bg-muted px-3 py-2"
            >
              <span className="truncate">
                {f.name}
                <span className="text-muted-foreground ml-2">
                  ({formatFileSize(f.size)})
                </span>
              </span>
              <button
                type="button"
                className="text-muted-foreground hover:text-foreground ml-2 shrink-0"
                disabled={disabled}
                onClick={() =>
                  onFilesChange(files.filter((_, idx) => idx !== i))
                }
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
