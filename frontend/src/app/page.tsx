"use client";

import {
  ArrowRight,
  FileSearch,
  Loader2,
  Sparkles,
  Upload,
  Workflow,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AppHeader } from "@/components/app-header";
import { UploadZone } from "@/components/upload-zone";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useUser } from "@/hooks/use-user";
import { ApiError, runAdhoc, uploadFiles } from "@/lib/api";
import { toastError } from "@/lib/toast";
import { ensureUser } from "@/lib/user-session";

const EXAMPLE_TASKS = [
  "Extract name, email, phone, company, and skills from these resumes. Output as JSON.",
  "Pull invoice number, vendor, amount, and date. Flag anything over ₹50,000. Give me CSV.",
  "Extract product name, SKU, quantity, and price from these purchase orders.",
];

const AGENT_TYPES = [
  "OCR",
  "Text extract",
  "Field extract",
  "Rules",
  "Formatter",
];

const HOW_IT_WORKS = [
  {
    icon: Upload,
    title: "Upload documents",
    description: "Drop PDFs or images — up to 10 files per batch.",
  },
  {
    icon: Sparkles,
    title: "Describe your task",
    description: "Plain English. The AI planner picks the right agent pipeline.",
  },
  {
    icon: Workflow,
    title: "Get structured results",
    description: "Watch steps run live, then download JSON or CSV.",
  },
];

export default function HomePage() {
  const router = useRouter();
  const { user } = useUser();
  const [files, setFiles] = useState<File[]>([]);
  const [task, setTask] = useState("");
  const [loading, setLoading] = useState(false);
  const [phase, setPhase] = useState<string | null>(null);

  async function handleRun() {
    if (!files.length) {
      toastError("Add at least one document.");
      return;
    }
    if (!task.trim()) {
      toastError("Describe what you want extracted or done.");
      return;
    }

    setLoading(true);
    try {
      await ensureUser();
      setPhase("Uploading documents…");
      const upload = await uploadFiles(files);
      setPhase("Starting pipeline…");
      const run = await runAdhoc(upload.upload_id, task.trim());
      router.push(`/results/${run.run_id}`);
    } catch (e) {
      toastError(
        e instanceof ApiError ? e.message : "Something went wrong. Try again.",
      );
    } finally {
      setLoading(false);
      setPhase(null);
    }
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <AppHeader />
      <main className="mx-auto max-w-5xl px-4 py-10 space-y-12">
        <section className="relative overflow-hidden rounded-2xl border bg-gradient-to-br from-background via-background to-primary/5 px-6 py-10 sm:px-10">
          <div className="relative z-10 max-w-2xl space-y-4">
            <Badge variant="secondary" className="gap-1">
              <FileSearch className="h-3 w-3" />
              AI document pipelines
            </Badge>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-tight leading-tight">
              Describe your task. Upload documents.{" "}
              <span className="text-primary">AI does the rest.</span>
            </h1>
            <p className="text-muted-foreground text-lg">
              AgentFlow plans a multi-step pipeline — OCR, extraction, rules,
              formatting — and returns structured JSON or CSV. No manual field
              mapping.
            </p>
            {!user && (
              <p className="text-sm text-amber-700">
                <Link href="/account" className="underline font-medium">
                  Create an account
                </Link>{" "}
                to save workflows and revisit run history.
              </p>
            )}
            <div className="flex flex-wrap gap-2 pt-1">
              {AGENT_TYPES.map((agent) => (
                <Badge key={agent} variant="outline">
                  {agent}
                </Badge>
              ))}
            </div>
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-3">
          {HOW_IT_WORKS.map((item) => (
            <Card key={item.title} className="border-dashed">
              <CardHeader className="pb-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary mb-2">
                  <item.icon className="h-4 w-4" />
                </div>
                <CardTitle className="text-base">{item.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">{item.description}</p>
              </CardContent>
            </Card>
          ))}
        </section>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Documents</CardTitle>
              <CardDescription>PDFs, PNG, or JPG (max 10)</CardDescription>
            </CardHeader>
            <CardContent>
              <UploadZone
                files={files}
                onFilesChange={setFiles}
                disabled={loading}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Task description</CardTitle>
              <CardDescription>
                Plain English — what should the pipeline do?
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="task">Your task</Label>
                <Textarea
                  id="task"
                  placeholder={EXAMPLE_TASKS[0]}
                  rows={8}
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  disabled={loading}
                />
              </div>

              <div className="space-y-2">
                <p className="text-xs font-medium text-muted-foreground">
                  Try an example
                </p>
                <div className="flex flex-col gap-2">
                  {EXAMPLE_TASKS.map((example) => (
                    <button
                      key={example}
                      type="button"
                      onClick={() => setTask(example)}
                      disabled={loading}
                      className="text-left text-xs rounded-md border px-3 py-2 hover:bg-muted/60 transition-colors disabled:opacity-50 line-clamp-2"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>

              <Button
                className="w-full"
                size="lg"
                onClick={handleRun}
                disabled={loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {phase ?? "Running…"}
                  </>
                ) : (
                  <>
                    Run pipeline
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
