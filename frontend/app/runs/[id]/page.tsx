"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { API_URL, getResults, getStatus, wsUrl } from "@/lib/api";

const PHASES = ["Intake", "Prep", "Understand", "Deep", "Stats", "Synthesis", "Output"];
const AGENTS = [
  "DataValidationAgent","DataCleaningAgent","SchemaDetectionAgent","BusinessDomainDetectionAgent",
  "BusinessObjectiveDetectionAgent","DataProfilingAgent","FeatureEngineeringAgent","KPIDiscoveryAgent",
  "StatisticalAnalysisAgent","InsightGenerationAgent","VisualizationAgent","ReportingAgent",
];

function badge(status: string) {
  const m: Record<string,string> = { queued: "bg-slate-700", running: "bg-amber-500 text-slate-950", done: "bg-emerald-500 text-slate-950", failed: "bg-red-600" };
  return m[status] || "bg-slate-700";
}

export default function RunPage() {
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<any>(null);
  const [results, setResults] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  // polling fallback
  useEffect(() => {
    if (!id) return;
    let t: any;
    const poll = async () => {
      try {
        const s = await getStatus(id);
        setStatus(s);
        setEvents(s.events || []);
        if (s.status === "done") {
          try { const r = await getResults(id); setResults(r); } catch {}
        } else if (s.status === "failed") {
          try { const r = await getResults(id); setResults(r); } catch {}
        }
      } catch {}
      if (!status || (status.status !== "done" && status.status !== "failed")) {
        t = setTimeout(poll, 2500);
      }
    };
    poll();
    return () => clearTimeout(t);
  }, [id, status?.status]);

  // websocket live
  useEffect(() => {
    if (!id) return;
    try {
      const ws = new WebSocket(wsUrl(id));
      wsRef.current = ws;
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "node" || msg.type === "status" || msg.type === "done" || msg.type === "error") {
            setEvents((prev) => [...prev.slice(-80), msg]);
            if (msg.steps_completed) setStatus((s: any) => s ? { ...s, steps_completed: msg.steps_completed, current_phase: msg.current_phase } : s);
            if (msg.type === "done" || msg.type === "error") {
              getResults(id).then(setResults).catch(()=>{});
              getStatus(id).then(setStatus).catch(()=>{});
            }
          }
        } catch {}
      };
      return () => { try { ws.close(); } catch {} };
    } catch {}
  }, [id]);

  const done = status?.status === "done";
  const failed = status?.status === "failed";
  const steps: string[] = status?.steps_completed || [];

  const phase = status?.current_phase || 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-bold font-mono">Run {id?.slice(0, 8)}</h1>
        <span className={`rounded px-3 py-1 text-sm font-semibold ${badge(status?.status || "queued")}`}>{status?.status || "…"}</span>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
        <div className="flex gap-1.5">
          {PHASES.map((p, i) => (
            <div key={p} className={`h-2 flex-1 rounded ${i + 1 <= phase ? "bg-emerald-500" : "bg-slate-800"}`} title={`Phase ${i + 1}: ${p}`} />
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-400">Phase {phase} / 7 • {steps.length} agents done • Domain: {status?.business_domain || "detecting…"}</p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
        <h2 className="font-semibold">Agent graph (live)</h2>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
          {AGENTS.map((a) => {
            const isDone = steps.includes(a);
            const short = a.replace("Agent","").replace("Data","").replace("Business","");
            return (
              <div key={a} className={`rounded border px-3 py-2 text-xs ${isDone ? "border-emerald-700 bg-emerald-950 text-emerald-200" : "border-slate-800 bg-slate-950 text-slate-400"}`}>
                <div className="font-mono truncate" title={a}>{short}</div>
                <div>{isDone ? "✓ done" : "… pending"}</div>
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-xs text-slate-500">Live via WebSocket {API_URL.replace("http","ws")}/ws/{id} • polling fallback every 2.5s</p>
      </div>

      {events.length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-4">
          <h3 className="text-sm font-semibold text-slate-300">Recent events</h3>
          <pre className="mt-2 max-h-48 overflow-auto rounded bg-black/40 p-3 font-mono text-xs text-slate-300">{JSON.stringify(events.slice(-12), null, 2)}</pre>
        </div>
      )}

      {failed && (
        <div className="rounded border border-red-900 bg-red-950 p-4 text-sm text-red-200">
          <strong>Run failed:</strong> {status.error || results?.error || "Unknown error"}
        </div>
      )}

      {done && results && (
        <div className="space-y-4">
          <div className="rounded-xl border border-emerald-800 bg-emerald-950/40 p-4">
            <h2 className="font-semibold text-emerald-200">Analysis complete ✓ — {results.duration_s ? `${results.duration_s.toFixed(1)}s` : ""}</h2>
            <div className="mt-2 flex flex-wrap gap-2 text-xs">
              {results.report_urls?.html && <a href={`${API_URL}${results.report_urls.html}`} target="_blank" className="rounded bg-emerald-600 px-3 py-1.5 text-white hover:bg-emerald-500">Open HTML report</a>}
              {results.report_urls?.json && <a href={`${API_URL}${results.report_urls.json}`} target="_blank" className="rounded border border-slate-600 px-3 py-1.5 hover:bg-slate-800">Download JSON</a>}
              <span className="rounded bg-slate-800 px-3 py-1.5">{results.counts?.kpis ?? 0} KPIs • {results.counts?.insights ?? 0} insights • {results.counts?.visualizations ?? 0} viz</span>
            </div>
          </div>

          {results.kpis?.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h3 className="font-semibold">KPIs</h3>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {results.kpis.map((k: any, i: number) => (
                  <div key={i} className="rounded border border-slate-800 bg-slate-950 p-3">
                    <div className="text-xs uppercase text-slate-400">{k.abbreviation || k.name}</div>
                    <div className="text-lg font-bold">{typeof k.value === "number" ? k.value.toFixed(2) : String(k.value ?? "—")}</div>
                    <div className="text-xs text-slate-400">{k.trend || "stable"} • {k.name}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {results.insights?.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h3 className="font-semibold">Top insights</h3>
              <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-200">
                {results.insights.slice(0, 8).map((ins: any, i: number) => (
                  <li key={i}><span className="font-semibold">{ins.title || ins.category}</span> — {ins.summary || ins.business_action || ""} <span className="text-xs text-slate-500">({ins.severity}, {Math.round((ins.confidence||0)*100)}%)</span></li>
                ))}
              </ol>
            </div>
          )}

          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h3 className="font-semibold">Execution trace</h3>
            <p className="mt-2 font-mono text-xs text-slate-400">{(results.trace?.steps_completed || steps).join(" → ")}</p>
          </div>
        </div>
      )}

      <p className="text-xs text-slate-500">Run ID: {id} • <a href={`${API_URL}/api/status/${id}`} target="_blank" className="underline">raw status</a> • <a href={`${API_URL}/api/results/${id}`} target="_blank" className="underline">raw results</a></p>
    </div>
  );
}
