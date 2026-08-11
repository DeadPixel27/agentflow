"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { ModalShell } from "@/components/modals/modal-shell";
import { UsageLimitModal } from "@/components/modals/usage-limit-modal";
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
  const [showUsageLimit, setShowUsageLimit] = useState(false);
  const [usageLimitMsg, setUsageLimitMsg] = useState("");

  useEffect(() => {
    if (!open) return;
    setTo(defaultTo || "");
  }, [open, defaultTo]);

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
      if (e instanceof ApiError && e.status === 429) {
        toastError(e.message);
        setUsageLimitMsg(e.message);
        setShowUsageLimit(true);
      } else {
        toastError(
          e instanceof ApiError
            ? e.message
            : "Email delivery is not available yet.",
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
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
          <p className="text-xs text-muted-foreground">
            Nexora emails results from its own sender address. No inbox sharing
            required — enter the recipient only.
          </p>
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
      <UsageLimitModal
        open={showUsageLimit}
        onClose={() => setShowUsageLimit(false)}
        message={usageLimitMsg}
      />
    </>
  );
}
