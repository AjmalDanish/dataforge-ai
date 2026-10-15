export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

// localtunnel adds a browser warning that is bypassed via this header
const LT_HEADERS: Record<string, string> = API_URL.includes("loca.lt")
  ? { "bypass-tunnel-reminder": "true" }
  : {};

export type RunStatus = "queued" | "running" | "done" | "failed";

export interface AgentEvent {
  type: "agent";
  agent: string;
  decision: string;
  success: boolean;
  message: string;
  duration_s: number;
  phase: number;
  step: number;
  ts: string;
}

export interface LifecycleEvent {
  type: "status" | "done" | "error" | "ping";
  status?: RunStatus;
  error?: string | null;
  duration_s?: number;
  ts: string;
}

export type RunEvent = AgentEvent | LifecycleEvent;

export interface Status {
  run_id: string;
  filename: string;
  status: RunStatus;
  current_phase: number;
  steps_completed: string[];
  steps_skipped: string[];
  business_domain: string | null;
  created_at: string;
  duration_s: number | null;
  error: string | null;
  llm: string | null;
  events: RunEvent[];
}

export interface Kpi {
  name: string;
  value: number | string | null;
  trend?: string;
  formula?: string;
  abbreviation?: string;
}

export interface Insight {
  category: string;
  title: string;
  summary: string;
  severity: string;
  business_action?: string;
  confidence?: number;
}

export interface Results {
  run_id: string;
  status: RunStatus;
  error?: string;
  filename?: string;
  business_domain?: string;
  domain_confidence?: number | null;
  duration_s?: number;
  llm?: string | null;
  kpis: Kpi[];
  insights: Insight[];
  narrative?: { narrative: string; recommendations: string[] } | null;
  evaluation?: { passed: boolean; failed_checks: string[] } | null;
  report_urls: { html: string | null; json: string | null; pdf: string | null };
  report_view_url: string | null;
  charts: { name: string; url: string }[];
  counts: { kpis: number; insights: number; visualizations: number };
  trace: { steps_completed: string[]; steps_skipped: string[] };
}

export function apiUrl(path: string): string {
  return `${API_URL}${path}`;
}

export function wsUrl(runId: string): string {
  return `${API_URL.replace(/^http/, "ws")}/ws/${runId}`;
}

async function json<T>(r: Response, what: string): Promise<T> {
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail?.detail || body.detail || `${what} failed: ${r.status}`);
  }
  return r.json() as Promise<T>;
}

export async function analyze(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${API_URL}/api/analyze`, { method: "POST", body: fd, headers: LT_HEADERS });
  return json<{ run_id: string; status: RunStatus; ws_url: string }>(r, "Upload");
}

export async function analyzeSample(name: string) {
  const r = await fetch(`/samples/${name}`);
  if (!r.ok) throw new Error(`Sample ${name} not found`);
  const blob = await r.blob();
  return analyze(new File([blob], name, { type: "text/csv" }));
}

export async function getStatus(runId: string) {
  const r = await fetch(`${API_URL}/api/status/${runId}`, { cache: "no-store", headers: LT_HEADERS });
  return json<Status>(r, "Status");
}

export async function getResults(runId: string) {
  const r = await fetch(`${API_URL}/api/results/${runId}`, { cache: "no-store", headers: LT_HEADERS });
  return json<Results>(r, "Results");
}

export async function getHistory(limit = 20) {
  const r = await fetch(`${API_URL}/api/history?limit=${limit}`, { cache: "no-store", headers: LT_HEADERS });
  return json<{ runs: Status[]; count: number }>(r, "History");
}
