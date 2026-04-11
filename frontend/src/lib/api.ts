export const API_BASE = "";

export interface TaskInfo {
  name: string;
  task: string;
  description: string;
  row_count: number;
  issue_count: number;
}

export interface StepLog {
  step: number;
  action: string;
  reward: number;
  done: boolean;
  issues_remaining: number;
}

export interface CleanResult {
  task: string;
  original_data: Record<string, any>[];
  final_data: Record<string, any>[];
  actions: string[];
  rewards: number[];
  score: number;
  grade: number;
  steps_log: StepLog[];
  final_issues: Record<string, any>[];
  metrics: Record<string, any>;
  model_used: string;
}

export interface Diagnostics {
  gemini_api_key: string;
  api_base: string;
  model: string;
  python_version: string;
  tasks: string[];
}

export async function fetchTasks(): Promise<TaskInfo[]> {
  const res = await fetch(`${API_BASE}/api/tasks`);
  if (!res.ok) throw new Error("Failed to fetch tasks");
  return res.json();
}

/** Alias for backward compatibility */
export const fetchDatasets = fetchTasks;

export async function fetchDiagnostics(): Promise<Diagnostics> {
  const res = await fetch(`${API_BASE}/api/diagnostics`);
  if (!res.ok) throw new Error("Failed to fetch diagnostics");
  return res.json();
}

export async function uploadDataset(file: File): Promise<{ task: string; row_count: number }> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function fetchOriginalData(): Promise<Record<string, any>[]> {
  const res = await fetch(`${API_BASE}/api/original-data`);
  if (!res.ok) throw new Error("Failed to fetch original data");
  return res.json();
}

export async function fetchTaskPreview(taskId: string): Promise<Record<string, any>[]> {
  const res = await fetch(`${API_BASE}/api/tasks/${taskId}/preview`);
  if (!res.ok) throw new Error("Failed to fetch preview");
  return res.json();
}

export async function reviewManualAudit(userInput: string): Promise<{ score: number; critique: string }> {
  const res = await fetch(`${API_BASE}/api/review-input`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_input: userInput }),
  });
  if (!res.ok) throw new Error("Review failed");
  return res.json();
}

export async function runCleaning(task: string): Promise<CleanResult> {
  const res = await fetch(`${API_BASE}/api/clean`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task, mode: "baseline" }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail?.[0]?.msg || err.detail || "Cleaning pipeline failed");
  }
  return res.json();
}
