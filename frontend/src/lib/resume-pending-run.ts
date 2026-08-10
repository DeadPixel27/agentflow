/** Execute a claimed pending home run and return the new run_id. */

import {
  runAdhoc,
  runTemplate,
  uploadFiles,
} from "@/lib/api";
import {
  claimPendingRun,
  savePendingRun,
  type PendingRun,
} from "@/lib/pending-run";

async function runSample(): Promise<string> {
  const response = await fetch("/samples/sample-invoice.pdf");
  if (!response.ok) {
    throw new Error("Sample invoice is missing.");
  }
  const blob = await response.blob();
  const file = new File([blob], "sample-invoice.pdf", {
    type: "application/pdf",
  });
  const upload = await uploadFiles([file]);
  const run = await runTemplate(upload.upload_id, "invoice");
  return run.run_id;
}

async function runPending(pending: PendingRun): Promise<string> {
  if (pending.kind === "sample") {
    return runSample();
  }
  if (!pending.files.length) {
    throw new Error("Your documents could not be restored. Please upload again.");
  }
  if (!pending.task.trim() && !pending.templateId) {
    throw new Error("Missing extraction task. Please try again.");
  }
  const upload = await uploadFiles(pending.files);
  const run = pending.templateId
    ? await runTemplate(upload.upload_id, pending.templateId)
    : await runAdhoc(upload.upload_id, pending.task.trim());
  return run.run_id;
}

/**
 * If a pending home run exists, claim it, start the pipeline, and return run_id.
 * On failure, re-saves the intent when possible so home can retry.
 * Returns null when there is nothing pending.
 */
export async function resumePendingRun(): Promise<string | null> {
  const pending = await claimPendingRun();
  if (!pending) return null;

  try {
    return await runPending(pending);
  } catch (err) {
    try {
      await savePendingRun({
        kind: pending.kind,
        files: pending.files,
        templateId: pending.templateId,
        task: pending.task,
      });
    } catch {
      /* ignore re-save failures */
    }
    throw err;
  }
}
