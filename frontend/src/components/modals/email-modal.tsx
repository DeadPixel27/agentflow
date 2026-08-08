"use client";

import { Loader2 } from "lucide-react";
import { useState } from "react";

import { ModalShell } from "@/components/modals/modal-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, emailResults } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";

interface EmailModalProps {
  open: boolean;
  onClose: () => void;
  runId: string;
  defaultTo?: string;
}

export function EmailModal({ open, onClose, runId, defaultTo = "" }: EmailModalProps) {
  const [to, setTo] = useState(defaultTo);
  const [subject, setSubject] = useState("Pipeline results");
  const [loading, setLoading] = useState(false);

  async function handleSend() {
    if (!to.trim()) {
      toastError("Enter a recipient email.");
      return;
    }
    setLoading(true);
    try {
      await emailResults(runId, to.trim(), subject.trim());
      toastSuccess("Results emailed.");
      onClose();
    } catch (e) {
      toastError(
        e instanceof ApiError
          ? e.message
          : "Email delivery is not available yet.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Email results"
      description="Send extracted data to a recipient."
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={() => void handleSend()} disabled={loading}>
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Send
          </Button>
        </>
      }
    >
      <div className="space-y-2">
        <Label htmlFor="email-to">To</Label>
        <Input
          id="email-to"
          type="email"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          placeholder="team@company.com"
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="email-subject">Subject</Label>
        <Input
          id="email-subject"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
        />
      </div>
    </ModalShell>
  );
}
