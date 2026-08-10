"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ModalShell } from "@/components/modals/modal-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, saveWorkflowFromRun } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";
import {
  ensureUser,
  getStoredUserId,
  SignInRequiredError,
} from "@/lib/user-session";

interface SaveWorkflowModalProps {
  open: boolean;
  onClose: () => void;
  runId: string;
  onSaved: (workflowId: string) => void;
}

export function SaveWorkflowModal({
  open,
  onClose,
  runId,
  onSaved,
}: SaveWorkflowModalProps) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSave() {
    if (!name.trim()) {
      toastError("Enter a workflow name.");
      return;
    }
    setLoading(true);
    try {
      const userId = getStoredUserId() ?? (await ensureUser());
      const wf = await saveWorkflowFromRun(runId, userId, name.trim());
      toastSuccess("Workflow saved.");
      onSaved(wf.workflow_id);
      onClose();
      router.push("/workflows");
    } catch (e) {
      if (e instanceof SignInRequiredError) {
        toastError("Sign in to save workflows.");
        onClose();
        router.push("/account");
      } else {
        toastError(
          e instanceof ApiError ? e.message : "Failed to save workflow.",
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Save as workflow"
      description="Reuse this pipeline on new uploads without re-planning."
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={() => void handleSave()} disabled={loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save
          </Button>
        </>
      }
    >
      <div className="space-y-2">
        <Label htmlFor="wf-name">Workflow name</Label>
        <Input
          id="wf-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Invoice extraction"
        />
      </div>
    </ModalShell>
  );
}
