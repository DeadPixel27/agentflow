"use client";

import { Loader2, Play } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { UploadZone } from "@/components/upload-zone";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError, runWorkflow, uploadFiles } from "@/lib/api";
import { toastError } from "@/lib/toast";

interface RerunPanelProps {
  workflowId: string;
  workflowName: string;
}

export function RerunPanel({ workflowId, workflowName }: RerunPanelProps) {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState<string | null>(null);

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
      router.push(`/results/${run.run_id}`);
    } catch (e) {
      toastError(
        e instanceof ApiError ? e.message : "Failed to run workflow.",
      );
    } finally {
      setLoading(false);
      setPhase(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Rerun workflow</CardTitle>
        <CardDescription>
          Upload new documents — runs &quot;{workflowName}&quot; without
          re-planning.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <UploadZone files={files} onFilesChange={setFiles} disabled={loading} />
        <Button className="w-full" onClick={handleRerun} disabled={loading}>
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
      </CardContent>
    </Card>
  );
}
