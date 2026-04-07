// ✅ Use proper env variable (works on Hugging Face)
export const API_BASE =
  process.env.NEXT_PUBLIC_ENV_API_URL || "";

// -------------------------------------------------------------------
// TYPES
// -------------------------------------------------------------------

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

export interface AuditReward {
  tier: string;
  points: number;
  message: string;
}

export interface AuditResult {
  score: number;
  critique: string;
  reward: AuditReward;
  final_data?: Record<string, any>[];
}

// -------------------------------------------------------------------
// SAFE FETCH HELPER (VERY IMPORTANT)
// -------------------------------------------------------------------

async function safeFetch(url: string, options?: RequestInit) {
  try {
    const res = await fetch(url, options);

    if (!res.ok) {
      let err;
      try {
        err = await res.json();
      } catch {
        err = { detail: "Unknown error" };
      }
      throw new Error(err.detail || "API Error");
    }

    return res.json();
  } catch (error: any) {
    console.error("API ERROR:", error.message);
    throw new Error(`Frontend cannot reach backend: ${error.message}`);
  }
}

// -------------------------------------------------------------------
// API FUNCTIONS
// -------------------------------------------------------------------

export async function fetchTasks(): Promise<TaskInfo[]> {
  return safeFetch(`${API_BASE}/api/tasks`);
}

export const fetchDatasets = fetchTasks;

export async function fetchDiagnostics(): Promise<Diagnostics> {
  return safeFetch(`${API_BASE}/api/diagnostics`);
}

export async function uploadDataset(
  file: File
): Promise<{ task: string; row_count: number }> {
  const formData = new FormData();
  formData.append("file", file);

  return safeFetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: formData,
  });
}

export async function fetchOriginalData(): Promise<Record<string, any>[]> {
  return safeFetch(`${API_BASE}/api/original-data`);
}

export async function reviewManualAudit(
  userInput: string
): Promise<AuditResult> {
  return safeFetch(`${API_BASE}/api/review-input`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ user_input: userInput }),
  });
}

export async function resetDataset(
  task: string
): Promise<{ status: string }> {
  return safeFetch(`${API_BASE}/api/reset`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ task }),
  });
}

export async function runCleaning(
  task: string
): Promise<CleanResult> {
  return safeFetch(`${API_BASE}/api/clean`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ task }),
  });
}