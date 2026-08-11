"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ModalShell } from "@/components/modals/modal-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, updateWorkflowFromRun } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";

interface SaveVersionModalProps {
  open: boolean;
  onClose: () => void;
  workflowId: string;
  runId: string;
  onSaved?: () => void;
}

export function SaveVersionModal({
  open,
  onClose,
  workflowId,
  runId,
  onSaved,
}: SaveVersionModalProps) {
  const router = useRouter();
  const [versionName, setVersionName] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSave() {
    setLoading(true);
    try {
      await updateWorkflowFromRun(
        workflowId,
        runId,
        versionName.trim() || undefined,
      );
      toastSuccess("New version saved.");
      onSaved?.();
      onClose();
      router.push(`/workflows/${workflowId}`);
    } catch (e) {
      toastError(
        e instanceof ApiError
          ? e.message
          : "Saving workflow versions is not available yet.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Save as new version"
      description="Capture refinements from this run as the next workflow version."
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={() => void handleSave()} disabled={loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save version
          </Button>
        </>
      }
    >
      <div className="space-y-2">
        <Label htmlFor="version-name">Version name (optional)</Label>
        <Input
          id="version-name"
          value={versionName}
          onChange={(e) => setVersionName(e.target.value)}
          placeholder="Added payment_status field"
        />
      </div>
    </ModalShell>
  );
}
