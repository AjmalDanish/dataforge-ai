export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// localtunnel adds a browser warning that is bypassed via this header
const LT_HEADERS: Record<string, string> = API_URL.includes("loca.lt")
  ? { "bypass-tunnel-reminder": "true" }
  : {};

export function wsUrl(runId: string): string {
  const base = API_URL.replace(/^http/, "ws");
  return `${base}/ws/${runId}`;
}

export async function analyze(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${API_URL}/api/analyze`, { method: "POST", body: fd, headers: LT_HEADERS });
  if (!r.ok) {
    const j = await r.json().catch(() => ({}));
    throw new Error(j.detail?.detail || j.detail || `Upload failed: ${r.status}`);
  }
  return (await r.json()) as {
    run_id: string;
    status: string;
    status_url: string;
    ws_url: string;
  };
}

export async function getStatus(runId: string) {
  const r = await fetch(`${API_URL}/api/status/${runId}`, { cache: "no-store", headers: LT_HEADERS });
  if (!r.ok) throw new Error(`status ${r.status}`);
  return r.json();
}

export async function getResults(runId: string) {
  const r = await fetch(`${API_URL}/api/results/${runId}`, { cache: "no-store", headers: LT_HEADERS });
  if (!r.ok) throw new Error(`results ${r.status}`);
  return r.json();
}

export async function getHistory(limit = 20) {
  const r = await fetch(`${API_URL}/api/history?limit=${limit}`, { cache: "no-store", headers: LT_HEADERS });
  if (!r.ok) throw new Error(`history ${r.status}`);
  return r.json();
}
