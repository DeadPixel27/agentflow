"use client";

import { Copy, Loader2 } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { NavBar } from "@/components/nav-bar";
import { PageHeader } from "@/components/page-header";
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
    } catch (e) {
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

  function copyInbound() {
    const addr = `flow-${workflowId.slice(0, 6)}@ingest.agentflow.dev`;
    void navigator.clipboard.writeText(addr);
    toastSuccess("Copied forwarding address.");
  }

  async function handleDelete() {
    const name = workflow?.name ?? "this workflow";
    const confirmed = window.confirm(
      `Delete "${name}"? This cannot be undone. Past runs will remain but will no longer be linked to this workflow.`,
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

  return (
    <div className="v2-page">
      <NavBar />
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
            <div className="space-y-2">
              <Label htmlFor="email">Email recipient</Label>
              <Input
                id="email"
                value={emailRecipient}
                onChange={(e) => setEmailRecipient(e.target.value)}
                placeholder="team@company.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sheets">Google Sheets URL</Label>
              <Input
                id="sheets"
                value={sheetsUrl}
                onChange={(e) => setSheetsUrl(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="sheet">Sheet name</Label>
              <Input
                id="sheet"
                value={sheetName}
                onChange={(e) => setSheetName(e.target.value)}
              />
            </div>
            <Button onClick={() => void handleSaveDelivery()} disabled={saving}>
              Update
            </Button>
          </AccountCard>

          <AccountCard title="Inbound Email">
            <div className="rounded-lg bg-blue-50 border border-blue-100 p-4 space-y-2">
              <p className="text-xs text-blue-900">
                Forward documents to this address to trigger this workflow.
              </p>
              <div className="flex items-center gap-2">
                <code className="text-xs flex-1 truncate">
                  flow-{workflowId.slice(0, 6)}@ingest.agentflow.dev
                </code>
                <Button variant="outline" size="sm" onClick={copyInbound}>
                  <Copy className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
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
              Permanently delete this workflow, its versions, and inbound email
              configuration. Past run results are kept but unlinked from this
              workflow.
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
