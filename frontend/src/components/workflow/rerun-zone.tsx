"use client";

import { Loader2, Play } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { UsageLimitModal } from "@/components/modals/usage-limit-modal";
import { UploadZone } from "@/components/upload-zone";
import { Button } from "@/components/ui/button";
import { ApiError, runWorkflow, uploadFiles } from "@/lib/api";
import { toastError } from "@/lib/toast";

interface RerunZoneProps {
  workflowId: string;
  workflowName: string;
  versionLabel?: string;
}

export function RerunZone({
  workflowId,
  workflowName,
  versionLabel,
}: RerunZoneProps) {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState<string | null>(null);
  const [showUsageLimit, setShowUsageLimit] = useState(false);
  const [usageLimitMsg, setUsageLimitMsg] = useState("");

  async function handleRerun() {
    if (!files.length) {
      toastError("Add at least one document.");
      return;
    }
    setLoading(true);
    try {
      setPhase("Uploading…");
      const upload = await uploadFiles(files);
      setPhase("Starting workflow…");
      const run = await runWorkflow(workflowId, upload.upload_id);
      router.push(`/workflows/${workflowId}/runs/${run.run_id}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 429) {
        setUsageLimitMsg(e.message);
        setShowUsageLimit(true);
      } else {
        toastError(
          e instanceof ApiError ? e.message : "Failed to run workflow.",
        );
      }
    } finally {
      setLoading(false);
      setPhase(null);
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-5 space-y-4">
      <div>
        <h2 className="font-serif text-base font-semibold">Run on new files</h2>
        <p className="text-xs text-muted-foreground mt-1">
          Uses {versionLabel ?? "current pipeline"} — same steps as &quot;
          {workflowName}&quot;
        </p>
      </div>
      <UploadZone files={files} onFilesChange={setFiles} disabled={loading} />
      <Button className="w-full" onClick={() => void handleRerun()} disabled={loading}>
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            {phase ?? "Running…"}
          </>
        ) : (
          <>
            <Play className="mr-2 h-4 w-4" />
            Run on new upload
          </>
        )}
      </Button>
      <UsageLimitModal
        open={showUsageLimit}
        onClose={() => setShowUsageLimit(false)}
        message={usageLimitMsg}
      />
    </div>
  );
}
