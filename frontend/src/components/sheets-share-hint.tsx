"use client";

import { Copy, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  ApiError,
  getIntegrationsStatus,
  type IntegrationsStatus,
} from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";

interface SheetsShareHintProps {
  /** Compact single-paragraph tip for modals */
  compact?: boolean;
}

export function SheetsShareHint({ compact = false }: SheetsShareHintProps) {
  const [status, setStatus] = useState<IntegrationsStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const next = await getIntegrationsStatus();
        if (!cancelled) setStatus(next);
      } catch (e) {
        if (!cancelled) {
          toastError(
            e instanceof ApiError
              ? e.message
              : "Could not load Sheets setup details.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function copyEmail() {
    const email = status?.sheets_share_email;
    if (!email) return;
    void navigator.clipboard.writeText(email);
    toastSuccess("Copied Nexora Sheets email.");
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        Loading Sheets setup…
      </div>
    );
  }

  if (!status?.sheets_configured || !status.sheets_share_email) {
    return (
      <p className="text-xs text-muted-foreground">
        Sheets push is not configured on this server yet. Ask your admin to set
        <code className="mx-1">GOOGLE_SERVICE_ACCOUNT_JSON</code>.
      </p>
    );
  }

  if (compact) {
    return (
      <div className="rounded-md border bg-muted/40 px-3 py-2 space-y-2">
        <p className="text-xs text-muted-foreground leading-relaxed">
          Before pushing, open the spreadsheet in Google Sheets → Share → add
          this address as <span className="font-medium text-foreground">Editor</span>:
        </p>
        <div className="flex items-center gap-2">
          <code className="text-[11px] flex-1 truncate">{status.sheets_share_email}</code>
          <Button type="button" variant="outline" size="sm" onClick={copyEmail}>
            <Copy className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    );
  }

  return (
    <ol className="list-decimal space-y-2 pl-4 text-sm text-muted-foreground">
      <li>Create or open a Google Spreadsheet.</li>
      <li>
        Click <span className="font-medium text-foreground">Share</span>, paste
        this email, and set access to{" "}
        <span className="font-medium text-foreground">Editor</span>:
        <div className="mt-2 flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-2">
          <code className="text-xs flex-1 truncate text-foreground">
            {status.sheets_share_email}
          </code>
          <Button type="button" variant="outline" size="sm" onClick={copyEmail}>
            <Copy className="h-3.5 w-3.5" />
          </Button>
        </div>
      </li>
      <li>
        Paste the spreadsheet URL below and choose a sheet / tab name. Nexora
        appends rows to that tab (creates it if missing).
      </li>
    </ol>
  );
}
