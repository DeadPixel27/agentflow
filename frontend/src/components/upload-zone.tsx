"use client";

import { Upload } from "lucide-react";
import { useCallback, useState } from "react";

import { cn } from "@/lib/utils";

interface UploadZoneProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
  disabled?: boolean;
}

export function UploadZone({ files, onFilesChange, disabled }: UploadZoneProps) {
  const [dragging, setDragging] = useState(false);

  const addFiles = useCallback(
    (incoming: FileList | File[]) => {
      const list = Array.from(incoming).filter((f) =>
        [".pdf", ".png", ".jpg", ".jpeg"].some((ext) =>
          f.name.toLowerCase().endsWith(ext),
        ),
      );
      if (!list.length) return;
      onFilesChange([...files, ...list].slice(0, 10));
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
          if (!disabled) addFiles(e.dataTransfer.files);
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
            Up to 10 files — PDF, PNG, JPG
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
            onChange={(e) => e.target.files && addFiles(e.target.files)}
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
              <span className="truncate">{f.name}</span>
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
