"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { AppHeader } from "@/components/app-header";
import { UploadZone } from "@/components/upload-zone";
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
import { ApiError, runAdhoc, uploadFiles } from "@/lib/api";
import { ensureUser } from "@/lib/user-session";

const EXAMPLE_TASK =
  "Extract name, email, phone, company, and skills from these resumes. Output as JSON.";

export default function HomePage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [task, setTask] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState<string | null>(null);

  async function handleRun() {
    setError(null);
    if (!files.length) {
      setError("Add at least one document.");
      return;
    }
    if (!task.trim()) {
      setError("Describe what you want extracted or done.");
      return;
    }

    setLoading(true);
    try {
      await ensureUser();
      setPhase("Uploading documents…");
      const upload = await uploadFiles(files);
      setPhase("Planning and running pipeline…");
      const run = await runAdhoc(upload.upload_id, task.trim());
      router.push(`/results/${run.run_id}`);
    } catch (e) {
      const message =
        e instanceof ApiError ? e.message : "Something went wrong. Try again.";
      setError(message);
    } finally {
      setLoading(false);
      setPhase(null);
    }
  }

  return (
    <div className="min-h-screen bg-muted/30">
      <AppHeader />
      <main className="mx-auto max-w-5xl px-4 py-10 space-y-8">
        <section className="space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">
            Describe your task. Upload documents. AI does the rest.
          </h1>
          <p className="text-muted-foreground max-w-2xl">
            AgentFlow plans a multi-step pipeline, extracts structured data, and
            returns JSON or CSV — no manual field mapping.
          </p>
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
              <CardDescription>Plain English — what should the pipeline do?</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="task">Your task</Label>
                <Textarea
                  id="task"
                  placeholder={EXAMPLE_TASK}
                  rows={8}
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  disabled={loading}
                />
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
                  "Run pipeline"
                )}
              </Button>
              {error && (
                <p className="text-sm text-destructive" role="alert">
                  {error}
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
