"use client";

import { Loader2 } from "lucide-react";
import { useState } from "react";

import { ModalShell } from "@/components/modals/modal-shell";
import { UsageLimitModal } from "@/components/modals/usage-limit-modal";
import { SheetsShareHint } from "@/components/sheets-share-hint";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError, pushToSheets } from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";

interface SheetsModalProps {
  open: boolean;
  onClose: () => void;
  runId: string;
  defaultUrl?: string;
}

export function SheetsModal({
  open,
  onClose,
  runId,
  defaultUrl = "",
}: SheetsModalProps) {
  const [url, setUrl] = useState(defaultUrl);
  const [sheetName, setSheetName] = useState("Results");
  const [loading, setLoading] = useState(false);
  const [showUsageLimit, setShowUsageLimit] = useState(false);
  const [usageLimitMsg, setUsageLimitMsg] = useState("");

  async function handlePush() {
    if (!url.trim()) {
      toastError("Enter a Google Sheets URL.");
      return;
    }
    setLoading(true);
    try {
      await pushToSheets(runId, url.trim(), sheetName.trim());
      toastSuccess("Pushed to Google Sheets.");
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
            : "Sheets integration is not available yet.",
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
        title="Push to Google Sheets"
        description="Append extracted rows to a spreadsheet."
        footer={
          <>
            <Button variant="outline" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button onClick={() => void handlePush()} disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Push
            </Button>
          </>
        }
      >
        <SheetsShareHint compact />
        <div className="space-y-2">
          <Label htmlFor="sheets-url">Spreadsheet URL</Label>
          <Input
            id="sheets-url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://docs.google.com/spreadsheets/d/..."
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="sheet-name">Sheet name</Label>
          <Input
            id="sheet-name"
            value={sheetName}
            onChange={(e) => setSheetName(e.target.value)}
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
