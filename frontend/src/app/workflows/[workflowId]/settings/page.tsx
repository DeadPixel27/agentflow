"use client";

import { Loader2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { SheetsShareHint } from "@/components/sheets-share-hint";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  ApiError,
  deleteWorkflow,
  getWorkflow,
  getWorkflowTemplateVersions,
  revertWorkflowToVersion,
  updateWorkflowSettings,
  type TemplateVersionSummary,
  type WorkflowResponse,
} from "@/lib/api";
import { toastError, toastSuccess } from "@/lib/toast";
import { cn } from "@/lib/utils";
import { pricingHref, WAITLIST_SOURCES } from "@/lib/waitlist-source";

function AccountCard({
  title,
  children,
  danger,
}: {
  title: string;
  children: React.ReactNode;
  danger?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-card p-5 space-y-4",
        danger && "border-destructive/40",
      )}
    >
      <h2 className="font-serif text-base font-semibold">{title}</h2>
      {children}
    </div>
  );
}

export default function WorkflowSettingsPage() {
  const router = useRouter();
  const params = useParams();
  const workflowId = params.workflowId as string;

  const [workflow, setWorkflow] = useState<WorkflowResponse | null>(null);
  const [versions, setVersions] = useState<TemplateVersionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [emailRecipient, setEmailRecipient] = useState("");
  const [sheetsUrl, setSheetsUrl] = useState("");
  const [sheetName, setSheetName] = useState("Results");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [wf, vers] = await Promise.all([
        getWorkflow(workflowId),
        getWorkflowTemplateVersions(workflowId).catch(() => []),
      ]);
      setWorkflow(wf);
      setVersions(vers);
      setName(wf.name);
      setDescription(wf.description);
      setEmailRecipient(wf.default_email ?? "");
      setSheetsUrl(wf.default_sheets_url ?? "");
      setSheetName(wf.default_sheet_name?.trim() || "Results");
    } catch (e) {
      setWorkflow(null);
      toastError(e instanceof ApiError ? e.message : "Failed to load settings.");
    } finally {
      setLoading(false);
    }
  }, [workflowId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleSaveGeneral() {
    setSaving(true);
    try {
      await updateWorkflowSettings(workflowId, { name, description });
      toastSuccess("Workflow updated.");
      await load();
    } catch (e) {
      toastError(e instanceof ApiError ? e.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveDelivery() {
    setSaving(true);
    try {
      await updateWorkflowSettings(workflowId, {
        default_email: emailRecipient,
        default_sheets_url: sheetsUrl,
        default_sheet_name: sheetName.trim() || "Results",
      });
      toastSuccess("Delivery settings updated.");
    } catch (e) {
      toastError(
        e instanceof ApiError
          ? e.message
          : "Delivery settings are not available yet.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleSetCurrent(versionId: string) {
    try {
      await revertWorkflowToVersion(workflowId, versionId);
      toastSuccess("Active version updated.");
      await load();
    } catch (e) {
      toastError(e instanceof ApiError ? e.message : "Failed to update version.");
    }
  }

  async function handleDelete() {
    const wfName = workflow?.name ?? "this workflow";
    const confirmed = window.confirm(
      `Delete "${wfName}"? This cannot be undone. Past runs will remain but will no longer be linked to this workflow.`,
    );
    if (!confirmed) return;

    setDeleting(true);
    try {
      await deleteWorkflow(workflowId);
      toastSuccess("Workflow deleted.");
      router.push("/workflows");
    } catch (e) {
      toastError(e instanceof ApiError ? e.message : "Failed to delete workflow.");
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return (
      <div className="v2-page items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="v2-page">
        <PageHeader title="Workflow Settings" description="Couldn’t load this workflow" />
        <main className="flex-1 overflow-y-auto px-4 py-6">
          <div className="mx-auto max-w-[680px] space-y-4">
            <p className="text-sm text-muted-foreground">
              This workflow may have been deleted, or you may not have access.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" onClick={() => void load()}>
                Try again
              </Button>
              <Link href="/workflows">
                <Button type="button">Back to workflows</Button>
              </Link>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="v2-page">
      <PageHeader
        title="Workflow Settings"
        description={workflow?.name}
      />
      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-[680px] space-y-6">
          <Link
            href={`/workflows/${workflowId}`}
            className="text-sm text-muted-foreground hover:text-foreground"
          >
            ← Back to workflow
          </Link>

          <AccountCard title="General">
            <div className="space-y-2">
              <Label htmlFor="wf-name">Name</Label>
              <Input id="wf-name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="wf-desc">Description</Label>
              <Input
                id="wf-desc"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
            <Button onClick={() => void handleSaveGeneral()} disabled={saving}>
              Save
            </Button>
          </AccountCard>

          <AccountCard title="Default Delivery">
            <p className="text-sm text-muted-foreground">
              When set, results are emailed and/or pushed to Sheets automatically
              after every successful run. You can still use Export on any run for
              a one-off send.
            </p>

            <div className="space-y-2">
              <Label htmlFor="email">Email recipient</Label>
              <p className="text-xs text-muted-foreground">
                Nexora sends a results email from its own address (Resend).
                No inbox sharing is required — just enter who should receive it.
              </p>
              <Input
                id="email"
                value={emailRecipient}
                onChange={(e) => setEmailRecipient(e.target.value)}
                placeholder="team@company.com"
              />
            </div>

            <div className="space-y-3 border-t pt-4">
              <div className="space-y-1">
                <p className="text-sm font-medium leading-none">Google Sheets</p>
                <p className="text-xs text-muted-foreground">
                  Nexora writes with a Google service account. You must grant
                  that account Editor access on the spreadsheet first.
                </p>
              </div>
              <SheetsShareHint />
              <div className="space-y-2">
                <Label htmlFor="sheets">Spreadsheet URL</Label>
                <Input
                  id="sheets"
                  value={sheetsUrl}
                  onChange={(e) => setSheetsUrl(e.target.value)}
                  placeholder="https://docs.google.com/spreadsheets/d/..."
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="sheet-name">Sheet / tab name</Label>
                <p className="text-xs text-muted-foreground">
                  Nexora appends rows to this tab and creates it if it doesn&apos;t
                  exist.
                </p>
                <Input
                  id="sheet-name"
                  value={sheetName}
                  onChange={(e) => setSheetName(e.target.value)}
                  placeholder="Results"
                />
              </div>
            </div>

            <Button onClick={() => void handleSaveDelivery()} disabled={saving}>
              Update
            </Button>
          </AccountCard>

          <AccountCard title="Inbound Email">
            <p className="text-sm text-muted-foreground leading-relaxed">
              Imagine forwarding an invoice from your inbox and watching this
              workflow extract the fields — no upload UI required.
            </p>
            <div className="rounded-lg border bg-muted/40 px-4 py-3 space-y-2 text-sm text-muted-foreground">
              <p>
                <span className="font-medium text-foreground">How it will work:</span>{" "}
                each workflow gets a private address like{" "}
                <code className="text-xs">flow-••••@ingest.nexora.app</code>. You
                email or forward PDFs, PNGs, or JPGs to it; Nexora starts a run
                and can email results or push them to Sheets using Default Delivery
                above.
              </p>
              <p>
                <span className="font-medium text-foreground">Coming with Pro:</span>{" "}
                unique addresses, attachment intake, and the same extraction
                quality you get from upload today. We&apos;re collecting interest
                before turning it on.
              </p>
            </div>
            <Link
              href={pricingHref(WAITLIST_SOURCES.inboundEmail)}
              className="inline-flex"
            >
              <Button type="button" className="w-full sm:w-auto">
                Join Pro waitlist for inbound email
              </Button>
            </Link>
          </AccountCard>

          <AccountCard title="Versions">
            {versions.length === 0 && (
              <p className="text-sm text-muted-foreground">No versions yet.</p>
            )}
            <div className="space-y-2">
              {versions.map((v) => {
                const isCurrent =
                  v.version_id === workflow?.current_template_version_id ||
                  v.is_current;
                return (
                  <div
                    key={v.version_id}
                    className={cn(
                      "rounded-md border p-3 text-sm",
                      isCurrent && "border-l-[3px] border-l-primary bg-primary/5",
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">
                        v{v.version_number}
                        {isCurrent && (
                          <span className="ml-2 v2-badge-success">current</span>
                        )}
                      </span>
                      {!isCurrent && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => void handleSetCurrent(v.version_id)}
                        >
                          Set as current
                        </Button>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {v.refine_summary || "Initial version"}
                    </p>
                  </div>
                );
              })}
            </div>
          </AccountCard>

          <AccountCard title="Danger Zone" danger>
            <p className="text-sm text-muted-foreground">
              Permanently delete this workflow and its versions. Past run results
              are kept but unlinked from this workflow.
            </p>
            <Button
              variant="destructive"
              disabled={deleting}
              onClick={() => void handleDelete()}
            >
              {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete workflow
            </Button>
          </AccountCard>
        </div>
      </main>
    </div>
  );
}
