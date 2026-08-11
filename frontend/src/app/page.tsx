"use client";

import { ArrowRight, Loader2, Play, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { UsageLimitModal } from "@/components/modals/usage-limit-modal";
import { UploadZone } from "@/components/upload-zone";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSignIn } from "@/hooks/use-sign-in";
import {
  ApiError,
  getAccessToken,
  getTemplate,
  listTemplates,
  runAdhoc,
  runTemplate,
  uploadFiles,
  type PipelineTemplateSummary,
} from "@/lib/api";
import { savePendingRun } from "@/lib/pending-run";
import { resumePendingRun } from "@/lib/resume-pending-run";
import { toastError } from "@/lib/toast";
import { ensureUser, SignInRequiredError } from "@/lib/user-session";
import { cn } from "@/lib/utils";

export default function HomePage() {
  const router = useRouter();
  const { openSignIn } = useSignIn();
  const [files, setFiles] = useState<File[]>([]);
  const [task, setTask] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(
    null,
  );
  const [templates, setTemplates] = useState<PipelineTemplateSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState<string | null>(null);
  const [showUsageLimit, setShowUsageLimit] = useState(false);
  const [usageLimitMsg, setUsageLimitMsg] = useState("");
  const resumeStarted = useRef(false);

  useEffect(() => {
    listTemplates()
      .then((data) => setTemplates(data.templates))
      .catch(() => {
        /* templates optional */
      });
  }, []);

  async function handleSelectTemplate(templateId: string) {
    if (selectedTemplateId === templateId) {
      setSelectedTemplateId(null);
      return;
    }
    setSelectedTemplateId(templateId);
    try {
      const template = await getTemplate(templateId);
      setTask(template.default_task || template.task_description || "");
    } catch {
      /* keep current task */
    }
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  const promptSignIn = useCallback(
    async (intent: {
      kind: "run" | "sample";
      files?: File[];
      templateId?: string | null;
      task?: string;
    }) => {
      try {
        await savePendingRun(intent);
      } catch {
        /* best-effort; still open sign-in */
      }
      openSignIn();
    },
    [openSignIn],
  );

  const handleApiError = useCallback(
    async (
      err: unknown,
      intent?: {
        kind: "run" | "sample";
        files?: File[];
        templateId?: string | null;
        task?: string;
      },
    ) => {
      if (err instanceof SignInRequiredError) {
        if (intent) {
          await promptSignIn(intent);
        } else {
          openSignIn();
        }
        return;
      }
      if (err instanceof ApiError) {
        switch (err.status) {
          case 401:
            if (intent) {
              await promptSignIn(intent);
            } else {
              openSignIn();
            }
            break;
          case 429:
            setUsageLimitMsg(err.message);
            setShowUsageLimit(true);
            break;
          case 503:
            toastError(
              "Service is temporarily at capacity. Please try again in a few minutes.",
            );
            break;
          default:
            toastError(err.message);
        }
      } else {
        toastError(
          err instanceof Error
            ? err.message
            : "Something went wrong. Please try again.",
        );
      }
    },
    [openSignIn, promptSignIn],
  );

  const executeSample = useCallback(async () => {
    setPhase("Loading sample…");
    const response = await fetch("/samples/sample-invoice.pdf");
    if (!response.ok) {
      throw new Error("Sample invoice is missing.");
    }
    const blob = await response.blob();
    const file = new File([blob], "sample-invoice.pdf", {
      type: "application/pdf",
    });
    setPhase("Uploading sample…");
    const upload = await uploadFiles([file]);
    setPhase("Starting pipeline…");
    const run = await runTemplate(upload.upload_id, "invoice");
    router.push(`/results/${run.run_id}`);
  }, [router]);

  const executeRun = useCallback(
    async (runFiles: File[], runTask: string, templateId: string | null) => {
      setPhase("Uploading documents…");
      const upload = await uploadFiles(runFiles);
      setPhase("Starting pipeline…");
      const run = templateId
        ? await runTemplate(upload.upload_id, templateId)
        : await runAdhoc(upload.upload_id, runTask.trim());
      router.push(`/results/${run.run_id}`);
    },
    [router],
  );

  async function handleTrySample() {
    const intent = { kind: "sample" as const };
    setLoading(true);
    try {
      await ensureUser();
      await executeSample();
    } catch (err) {
      await handleApiError(err, intent);
    } finally {
      setLoading(false);
      setPhase(null);
    }
  }

  async function handleRun() {
    if (!files.length) {
      toastError("Add at least one document.");
      return;
    }
    if (!task.trim()) {
      toastError("Describe what you want extracted or done.");
      return;
    }

    const intent = {
      kind: "run" as const,
      files,
      templateId: selectedTemplateId,
      task: task.trim(),
    };

    setLoading(true);
    try {
      await ensureUser();
      await executeRun(files, task, selectedTemplateId);
    } catch (err) {
      await handleApiError(err, intent);
    } finally {
      setLoading(false);
      setPhase(null);
    }
  }

  useEffect(() => {
    // Backup if a pending intent remains after a failed dialog resume.
    if (!getAccessToken()) return;
    if (resumeStarted.current) return;
    resumeStarted.current = true;

    void (async () => {
      try {
        setLoading(true);
        setPhase("Starting your run…");
        const runId = await resumePendingRun();
        if (!runId) {
          setLoading(false);
          setPhase(null);
          return;
        }
        router.push(`/results/${runId}`);
      } catch (err) {
        setLoading(false);
        setPhase(null);
        await handleApiError(err);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once on mount
  }, []);

  return (
    <div className="v2-page">
      <main className="flex flex-1 flex-col items-center overflow-y-auto px-4 py-10">
        <div className="w-full max-w-[700px] space-y-6">
          <div className="text-center space-y-3">
            <h1 className="font-serif text-[30px] font-semibold leading-tight tracking-tight">
              Extract structured data from{" "}
              <em className="text-primary not-italic">any document</em>
            </h1>
            <p className="text-sm text-muted-foreground max-w-[520px] mx-auto">
              Upload invoices, receipts, reports — or forward them via email. AI
              extracts fields and returns structured JSON or CSV.
            </p>
          </div>

          <UploadZone files={files} onFilesChange={setFiles} disabled={loading} />

          {files.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {files.map((file, index) => (
                <span
                  key={`${file.name}-${index}`}
                  className="inline-flex items-center gap-1.5 rounded-md bg-surface-2 px-2.5 py-1 text-xs font-medium"
                >
                  {file.name}
                  <button
                    type="button"
                    onClick={() => removeFile(index)}
                    className="text-muted-foreground hover:text-foreground"
                    aria-label={`Remove ${file.name}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          {templates.length > 0 && (
            <div className="space-y-3">
              <div className="flex flex-wrap gap-2 justify-center">
                {templates.map((template) => (
                  <button
                    key={template.template_id}
                    type="button"
                    disabled={loading}
                    onClick={() => void handleSelectTemplate(template.template_id)}
                    className={cn(
                      "px-3 py-1.5 rounded-md text-[11px] font-semibold border transition-all",
                      "border-border bg-card hover:border-primary hover:bg-primary/5",
                      selectedTemplateId === template.template_id &&
                        "border-primary bg-primary/10 text-primary",
                    )}
                  >
                    {template.name}
                  </button>
                ))}
              </div>
              <div className="flex justify-center">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void handleTrySample()}
                  disabled={loading}
                  className="gap-2"
                >
                  <Play className="h-4 w-4" />
                  Try with sample invoice
                </Button>
              </div>
            </div>
          )}

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-background px-3 text-xs text-muted-foreground">
                or describe your task
              </span>
            </div>
          </div>

          <div className="flex gap-2">
            <Input
              placeholder="Extract vendor name, amount, due date…"
              value={task}
              onChange={(e) => setTask(e.target.value)}
              disabled={loading}
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleRun();
              }}
              className="flex-1"
            />
            <Button onClick={() => void handleRun()} disabled={loading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {phase ?? "Running…"}
                </>
              ) : (
                <>
                  Run
                  <ArrowRight className="ml-2 h-4 w-4" />
                </>
              )}
            </Button>
          </div>

          <p className="text-center text-xs text-muted-foreground pt-2">
            50 pages free · Results in seconds
          </p>
        </div>
      </main>
      <UsageLimitModal
        open={showUsageLimit}
        onClose={() => setShowUsageLimit(false)}
        message={usageLimitMsg}
      />
    </div>
  );
}
