/**
 * API client for the LLM Evaluation Platform.
 *
 * All requests are relative and routed through the Next.js server-side proxy
 * (src/app/api/[...path]/route.ts), which injects the API key. The browser never
 * talks to the backend directly and never sees the key, so there is no auth
 * header handling here.
 */

const API_BASE = "";

export interface EvaluationResult {
  relevance: number | null;
  hallucination: Record<string, unknown> | null;
  latency_ms: number | null;
  estimated_cost: number | null;
}

export interface MetricResult {
  metric: string;
  score: number;
  passed: boolean | null;
  evaluator_version: string;
  details: Record<string, unknown> | null;
  error?: string | null;
}

export interface EvaluationRun {
  run_id: string;
  created_at: string;
  status: string;
  profile: string | null;
  composite_score: number | null;
  results: EvaluationResult;
  metric_results: MetricResult[];
  is_baseline?: boolean; // not currently returned by the API
}

export interface JobProgress {
  total: number;
  completed: number;
  failed: number;
}

export interface EvaluationJob {
  job_id: string;
  status: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  progress: JobProgress | null;
  error_message: string | null;
  evaluation_run_id?: string | null;
}

export interface QualityGate {
  gate_id: string;
  name: string;
  thresholds: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
}

export interface Baseline {
  baseline_id: string;
  name: string;
  description: string;
  run_id: string;
  created_at: string;
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export async function getHealth() {
  return fetchJson<{ status: string }>("/health");
}

export async function getRuns(page = 1, size = 20): Promise<{ runs: EvaluationRun[]; total: number }> {
  const offset = (page - 1) * size;
  return fetchJson(`/api/v1/runs?offset=${offset}&limit=${size}`);
}

export async function getRun(runId: string): Promise<EvaluationRun> {
  return fetchJson(`/api/v1/runs/${runId}`);
}

export async function getJobs(page = 1, size = 20): Promise<{ jobs: EvaluationJob[]; total: number }> {
  const offset = (page - 1) * size;
  return fetchJson(`/api/v1/jobs?offset=${offset}&limit=${size}`);
}

export async function getJob(jobId: string): Promise<EvaluationJob> {
  return fetchJson(`/api/v1/jobs/${jobId}`);
}

export async function getQualityGates(): Promise<QualityGate[]> {
  return fetchJson("/api/v1/quality-gates");
}

export async function getBaselines(): Promise<Baseline[]> {
  return fetchJson("/api/v1/baselines");
}

export async function getProfiles(): Promise<{ profiles: Record<string, string[]> }> {
  return fetchJson("/api/v1/profiles");
}

export async function submitEvaluation(data: {
  conversation: { model_response: string };
  context: { chunks: { text: string }[] };
  profile?: string;
}): Promise<{ run_id: string; status: string; results: Record<string, unknown> }> {
  const res = await fetch(`${API_BASE}/api/v1/evaluations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export async function submitAsyncEvaluation(data: {
  items: { conversation: { model_response: string }; context: { chunks: { text: string }[] } }[];
}): Promise<{ job_id: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/v1/evaluations/async`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export async function cancelJob(jobId: string): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/v1/jobs/${jobId}/cancel`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}
