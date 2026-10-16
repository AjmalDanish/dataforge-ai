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

export interface RunLinks {
  run_page: string;
  files: string;
  ws: string;
}

export interface Status {
  run_id: string;
  share_token: string;
  links?: RunLinks;
  is_owner?: boolean;
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

export interface KpiTile {
  key: string;
  label: string;
  unit: "currency" | "count";
  value: number | null;
  current?: number | null;
  previous?: number | null;
  change_pct?: number | null;
  spark?: (number | null)[];
}

export interface DashboardSpec {
  kpis: string[];
  dimensions: string[];
  grain: string | null;
  filters: Record<string, string[]>;
}

export interface Dashboard {
  version_spec: DashboardSpec;
  options: { kpis: string[]; dimensions: string[]; grains: string[]; filters: Record<string, string[]> };
  date_range: [string, string] | null;
  period: { grain: string | null; current: string | null; previous: string | null };
  rows_in_view: number;
  kpis: KpiTile[];
  trend: Record<string, number | string | null>[];
  breakdowns: { dimension: string; metric: string; rows: { name: string; value: number; share_pct: number; orders?: number }[] }[];
  top_items: { dimension: string; rows: Record<string, number | string | null>[] } | null;
  heatmap: { metric: string; days: string[]; hours: number[]; cells: { day: string; hour: number; value: number }[] } | null;
}

export interface Brief {
  headline: string;
  summary: string;
  findings: { title: string; kpi: string; direction: "up" | "down" | "flat"; so_what: string }[];
  recommendations: { action: string; rationale: string; priority: "high" | "medium" | "low"; kpi: string }[];
  risks: string[];
  source: "llm" | "rules";
}

export interface VersionMeta {
  version: number;
  kind: "original" | "refined";
  created_at: string;
  instructions: string | null;
  headline: string | null;
  spec: DashboardSpec;
}

export interface VersionDoc {
  version: number;
  kind: "original" | "refined";
  created_at: string;
  instructions: string | null;
  dashboard: Dashboard;
  brief: Brief;
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
  dashboard: Dashboard | Record<string, never>;
  brief: Brief | null;
  versions: VersionMeta[];
  approved_version: number | null;
  llm_available: boolean;
  trace: { steps_completed: string[]; steps_skipped: string[] };
}

export function apiUrl(path: string): string {
  return `${API_URL}${path}`;
}

export function wsUrl(path: string): string {
  return `${API_URL.replace(/^http/, "ws")}${path}`;
}

type Token = string | null | undefined;

function headers(token: Token): Record<string, string> {
  return token ? { ...LT_HEADERS, Authorization: `Bearer ${token}` } : LT_HEADERS;
}

function withShare(path: string, share: Token): string {
  return share ? `${path}${path.includes("?") ? "&" : "?"}t=${encodeURIComponent(share)}` : path;
}

async function json<T>(r: Response, what: string): Promise<T> {
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail?.detail || body.detail || `${what} failed: ${r.status}`);
  }
  return r.json() as Promise<T>;
}

export interface Started extends RunLinks {
  run_id: string;
  status: RunStatus;
  share_token: string;
}

// A sleeping free-tier API holds the first request ~1 min while it boots, longer
// than a Clerk session token lives (60s). So wake the API first, then mint the token.
async function wakeApi() {
  await fetch(`${API_URL}/healthz`, { cache: "no-store", headers: LT_HEADERS, signal: AbortSignal.timeout(120_000) });
}

export async function analyze(file: File, getToken: () => Promise<Token>) {
  await wakeApi();
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${API_URL}/api/analyze`, { method: "POST", body: fd, headers: headers(await getToken()) });
  return json<Started>(r, "Upload");
}

export async function analyzeSample(name: string, getToken: () => Promise<Token>) {
  await wakeApi();
  const r = await fetch(`${API_URL}/api/samples/${encodeURIComponent(name)}`, {
    method: "POST",
    headers: headers(await getToken()),
  });
  return json<Started>(r, "Sample");
}

export async function getStatus(runId: string, share: Token, token: Token) {
  const r = await fetch(withShare(`${API_URL}/api/status/${runId}`, share), { cache: "no-store", headers: headers(token) });
  return json<Status>(r, "Status");
}

export async function getResults(runId: string, share: Token, token: Token) {
  const r = await fetch(withShare(`${API_URL}/api/results/${runId}`, share), { cache: "no-store", headers: headers(token) });
  return json<Results>(r, "Results");
}

export async function getHistory(token: Token, limit = 20) {
  const r = await fetch(`${API_URL}/api/history?limit=${limit}`, { cache: "no-store", headers: headers(token) });
  return json<{ runs: Status[]; count: number }>(r, "History");
}

export interface RefineRequest {
  kpis?: string[];
  dimensions?: string[];
  grain?: string | null;
  filters?: Record<string, string[]>;
  instructions?: string;
}

export async function refine(runId: string, body: RefineRequest, getToken: () => Promise<Token>) {
  await wakeApi();
  const r = await fetch(`${API_URL}/api/runs/${runId}/refine`, {
    method: "POST",
    headers: { ...headers(await getToken()), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return json<VersionDoc>(r, "Refine");
}

export async function approve(runId: string, version: number, getToken: () => Promise<Token>) {
  const r = await fetch(`${API_URL}/api/runs/${runId}/approve`, {
    method: "POST",
    headers: { ...headers(await getToken()), "Content-Type": "application/json" },
    body: JSON.stringify({ version }),
  });
  return json<{ approved_version: number }>(r, "Approve");
}

export async function getVersion(runId: string, n: number, share: Token, token: Token) {
  const r = await fetch(withShare(`${API_URL}/api/runs/${runId}/versions/${n}`, share), { cache: "no-store", headers: headers(token) });
  return json<VersionDoc>(r, "Version");
}
