"use client";

import { ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ApiError,
  getRunTemplateVersion,
  getRunTemplateVersions,
  getWorkflowTemplateVersion,
  getWorkflowTemplateVersions,
  revertRunToVersion,
  revertWorkflowToVersion,
  type TemplateVersionDetail,
  type TemplateVersionSummary,
} from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";

interface TemplateVersionPanelProps {
  scopeType: "run" | "workflow";
  scopeId: string;
  currentVersionId?: string | null;
  onWorkflowUpdated?: () => void | Promise<void>;
}

export function TemplateVersionPanel({
  scopeType,
  scopeId,
  currentVersionId,
  onWorkflowUpdated,
}: TemplateVersionPanelProps) {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [versions, setVersions] = useState<TemplateVersionSummary[]>([]);
  const [preview, setPreview] = useState<TemplateVersionDetail | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [reverting, setReverting] = useState<string | null>(null);

  const useVersionLabel =
    scopeType === "run" ? "Branch and refine" : "Use for next workflow run";

  const loadVersions = useCallback(async () => {
    setLoading(true);
    try {
      const list =
        scopeType === "run"
          ? await getRunTemplateVersions(scopeId)
          : await getWorkflowTemplateVersions(scopeId);
      setVersions(list);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setVersions([]);
      } else {
        toastError(e instanceof ApiError ? e.message : "Failed to load versions.");
      }
    } finally {
      setLoading(false);
    }
  }, [scopeId, scopeType]);

  useEffect(() => {
    if (expanded) {
      loadVersions();
    }
  }, [expanded, loadVersions]);

  async function handlePreview(versionId: string) {
    setPreviewLoading(true);
    try {
      const detail =
        scopeType === "run"
          ? await getRunTemplateVersion(scopeId, versionId)
          : await getWorkflowTemplateVersion(scopeId, versionId);
      setPreview(detail);
    } catch (e) {
      toastError(e instanceof ApiError ? e.message : "Failed to load version.");
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleUseVersion(versionId: string) {
    setReverting(versionId);
    try {
      if (scopeType === "run") {
        const result = await revertRunToVersion(scopeId, versionId);
        toastSuccess("Branched from earlier version.");
        router.push(`/results/${result.run_id}`);
      } else {
        await revertWorkflowToVersion(scopeId, versionId);
        toastSuccess("Workflow updated to selected version.");
        await loadVersions();
        if (onWorkflowUpdated) {
          await onWorkflowUpdated();
        }
      }
    } catch (e) {
      toastError(e instanceof ApiError ? e.message : "Failed to branch version.");
    } finally {
      setReverting(null);
    }
  }

  if (!expanded && versions.length === 0 && !loading) {
    return (
      <Card>
        <CardHeader className="cursor-pointer" onClick={() => setExpanded(true)}>
          <CardTitle className="text-base">Template versions</CardTitle>
          <CardDescription>View version history and branch from earlier versions.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        className="cursor-pointer"
        onClick={() => setExpanded((value) => !value)}
      >
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Template versions</CardTitle>
            <CardDescription>
              {versions.length
                ? `${versions.length} version(s)${currentVersionId ? " · viewing current" : ""}`
                : "Version history for this run or workflow"}
            </CardDescription>
          </div>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="space-y-4">
          {loading && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading versions…
            </div>
          )}

          {!loading && versions.length === 0 && (
            <p className="text-sm text-muted-foreground">No versions yet.</p>
          )}

          <ul className="space-y-2">
            {versions.map((version) => (
              <li
                key={version.version_id}
                className={`flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-md border p-3 text-sm ${
                  version.is_current ? "border-primary/50 bg-muted/40" : ""
                }`}
              >
                <div>
                  <p className="font-medium">
                    v{version.version_number}
                    {version.is_current ? " · current" : ""}
                  </p>
                  <p className="text-muted-foreground">{version.refine_summary}</p>
                  {version.created_at && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(version.created_at).toLocaleString()}
                    </p>
                  )}
                </div>
                <div className="flex gap-2 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePreview(version.version_id)}
                    disabled={previewLoading}
                  >
                    Preview
                  </Button>
                  {!version.is_current && (
                    <Button
                      size="sm"
                      onClick={() => handleUseVersion(version.version_id)}
                      disabled={reverting === version.version_id}
                    >
                      {reverting === version.version_id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        useVersionLabel
                      )}
                    </Button>
                  )}
                </div>
              </li>
            ))}
          </ul>

          {preview && (
            <div className="rounded-md border p-3 space-y-2">
              <p className="text-sm font-medium">
                Preview v{preview.version_number}: {preview.refine_summary}
              </p>
              <pre className="text-xs whitespace-pre-wrap bg-muted/50 p-2 rounded max-h-48 overflow-auto">
                {preview.extraction_prompt}
              </pre>
              <Button variant="ghost" size="sm" onClick={() => setPreview(null)}>
                Close preview
              </Button>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
