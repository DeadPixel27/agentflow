const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // ignore
    }
    throw new ApiError(String(detail), res.status);
  }
  return res.json() as Promise<T>;
}

export interface User {
  user_id: string;
  name: string;
  email: string;
  created_at: string | null;
}

export interface UploadedDocument {
  document_id: string;
  filename: string;
  file_type: string;
  storage_path: string;
  extracted_text?: string;
  extraction_method?: string;
}

export interface UploadResponse {
  upload_id: string;
  documents: UploadedDocument[];
  message: string;
}

export interface UploadedDocumentSummary {
  document_id: string;
  filename: string;
  file_type: string;
}

export interface UploadDocumentsResponse {
  upload_id: string;
  documents: UploadedDocumentSummary[];
}

export interface StepRun {
  step_order: number;
  agent_type: string;
  status: string;
  output: Record<string, unknown>;
  error_message?: string | null;
}

export interface PlannedStep {
  step_order: number;
  agent_type: string;
  config: Record<string, unknown>;
  reason: string;
}

export interface PipelineTemplateSummary {
  template_id: string;
  name: string;
  description: string;
  icon: string;
  category: string;
}

export interface PipelineTemplate extends PipelineTemplateSummary {
  task_description?: string;
  default_task: string;
  fields?: string[];
  extraction_instructions?: string;
  rules?: Record<string, unknown>[];
  output_format?: string;
  suggested_steps?: string[];
  example_output_fields?: string[];
  sort_order?: number;
}

export interface TemplateListResponse {
  templates: PipelineTemplateSummary[];
  count: number;
}

export interface RunResult {
  format?: string;
  content?: string;
  rows?: Record<string, unknown>[];
  row_count?: number;
}

export interface RunResponse {
  run_id: string;
  upload_id: string;
  task_description: string;
  status: string;
  document_ids: string[];
  steps: StepRun[];
  planned_steps: PlannedStep[];
  workflow_id: string | null;
  result: RunResult | null;
  error_message: string | null;
}

export interface WorkflowStep {
  step_order: number;
  agent_type: string;
  config: Record<string, unknown>;
  reason: string;
}

export interface WorkflowSummary {
  workflow_id: string;
  user_id: string;
  name: string;
  description: string;
  source: string;
  step_count: number;
  created_at: string | null;
}

export interface WorkflowResponse {
  workflow_id: string;
  user_id: string;
  name: string;
  description: string;
  source: string;
  task_description: string;
  steps: WorkflowStep[];
  created_at: string | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  persistence: string;
  database: string | null;
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export async function signIn(name: string, email: string): Promise<{
  user: User;
  is_new_user: boolean;
  auth_provider: string;
}> {
  return request("/api/auth/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email }),
  });
}

/** @deprecated Use signIn — kept for compatibility */
export async function createUser(name: string, email = ""): Promise<User> {
  const result = await signIn(name, email);
  return result.user;
}

export async function getUser(userId: string): Promise<User> {
  return request<User>(`/api/users/${userId}`);
}

export async function getUserWorkflows(userId: string): Promise<WorkflowSummary[]> {
  return request<WorkflowSummary[]>(`/api/users/${userId}/workflows`);
}

export async function getWorkflow(workflowId: string): Promise<WorkflowResponse> {
  return request<WorkflowResponse>(`/api/workflows/${workflowId}`);
}

export async function getWorkflowRuns(workflowId: string): Promise<RunResponse[]> {
  return request<RunResponse[]>(`/api/workflows/${workflowId}/runs`);
}

export async function runWorkflow(
  workflowId: string,
  uploadId: string,
): Promise<RunResponse> {
  return request<RunResponse>(`/api/workflows/${workflowId}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ upload_id: uploadId }),
  });
}

export async function uploadFiles(files: File[]): Promise<UploadResponse> {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
  return request<UploadResponse>("/api/upload", { method: "POST", body: form });
}

export async function getUploadDocuments(
  uploadId: string,
): Promise<UploadDocumentsResponse> {
  return request<UploadDocumentsResponse>(`/api/uploads/${uploadId}`);
}

export function inputDocumentUrl(uploadId: string, documentId: string): string {
  return `${API_BASE}/api/uploads/${uploadId}/documents/${documentId}`;
}

export async function listTemplates(category?: string): Promise<TemplateListResponse> {
  const query = category ? `?category=${encodeURIComponent(category)}` : "";
  return request<TemplateListResponse>(`/api/templates${query}`);
}

export async function getTemplate(templateId: string): Promise<PipelineTemplate> {
  return request<PipelineTemplate>(`/api/templates/${templateId}`);
}

export async function runTemplate(
  uploadId: string,
  templateId: string,
): Promise<RunResponse> {
  return request<RunResponse>("/api/runs/template", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      upload_id: uploadId,
      template_id: templateId,
    }),
  });
}

export async function runAdhoc(
  uploadId: string,
  taskDescription: string,
): Promise<RunResponse> {
  return request<RunResponse>("/api/runs/adhoc", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      upload_id: uploadId,
      task_description: taskDescription,
    }),
  });
}

export async function getRun(runId: string): Promise<RunResponse> {
  return request<RunResponse>(`/api/runs/${runId}`);
}

export async function saveWorkflowFromRun(
  runId: string,
  userId: string,
  name: string,
  description = "",
): Promise<WorkflowResponse> {
  return request<WorkflowResponse>(`/api/workflows/from-run/${runId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, name, description }),
  });
}

export function downloadJson(filename: string, data: unknown) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadCsv(filename: string, rows: Record<string, unknown>[]) {
  if (!rows.length) return;
  const keys = Object.keys(rows[0]);
  const escape = (v: unknown) => {
    const s = String(v ?? "");
    return s.includes(",") || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [
    keys.join(","),
    ...rows.map((row) => keys.map((k) => escape(row[k])).join(",")),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
