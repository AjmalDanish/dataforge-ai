"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import {
  AgentEvent,
  RunEvent,
  Results,
  Status,
  apiUrl,
  getResults,
  getStatus,
  wsUrl,
} from "@/lib/api";
import { useApiToken } from "@/lib/auth";

const PHASES = ["Intake", "Prep", "Understand", "Deep analysis", "Statistics", "Synthesis", "Output"];
const PIPELINE: { phase: number; agents: string[] }[] = [
  { phase: 1, agents: ["DataValidationAgent"] },
  { phase: 2, agents: ["DataCleaningAgent"] },
  { phase: 3, agents: ["SchemaDetectionAgent", "BusinessDomainDetectionAgent", "BusinessObjectiveDetectionAgent"] },
  { phase: 4, agents: ["DataProfilingAgent", "FeatureEngineeringAgent", "KPIDiscoveryAgent"] },
  { phase: 5, agents: ["StatisticalAnalysisAgent"] },
  { phase: 6, agents: ["InsightGenerationAgent"] },
  { phase: 7, agents: ["VisualizationAgent", "EvaluatorAgent", "ReportingAgent"] },
];
const ALL_AGENTS = PIPELINE.flatMap((p) => p.agents);
const TERMINAL = new Set(["done", "failed"]);

type NodeState = "done" | "running" | "retrying" | "skipped" | "pending";

function shortName(a: string) {
  return a.replace("Agent", "").replace("BusinessDomainDetection", "Domain").replace("BusinessObjectiveDetection", "Objectives")
    .replace("StatisticalAnalysis", "Statistics").replace("FeatureEngineering", "Features").replace("InsightGeneration", "Insights")
    .replace("SchemaDetection", "Schema").replace("KPIDiscovery", "KPIs").replace(/^Data/, "");
}

function statusBadge(status: string) {
  const m: Record<string, string> = {
    queued: "bg-slate-700",
    running: "bg-amber-500 text-slate-950 animate-pulse",
    done: "bg-emerald-500 text-slate-950",
    failed: "bg-red-600",
  };
  return m[status] || "bg-slate-700";
}

const NODE_STYLE: Record<NodeState, { fill: string; stroke: string; text: string; label: string }> = {
  done: { fill: "#064e3b", stroke: "#10b981", text: "#a7f3d0", label: "✓ done" },
  running: { fill: "#78350f", stroke: "#f59e0b", text: "#fde68a", label: "● running" },
  retrying: { fill: "#7f1d1d", stroke: "#f87171", text: "#fecaca", label: "↻ retrying" },
  skipped: { fill: "#1e293b", stroke: "#475569", text: "#64748b", label: "⊘ skipped" },
  pending: { fill: "#0f172a", stroke: "#334155", text: "#94a3b8", label: "… pending" },
};

function AgentGraph({ states }: { states: Record<string, NodeState> }) {
  const colW = 150;
  const nodeW = 124;
  const nodeH = 44;
  const gapY = 14;
  const top = 30;
  const maxRows = Math.max(...PIPELINE.map((p) => p.agents.length));
  const height = top + maxRows * (nodeH + gapY) + 10;
  const width = PIPELINE.length * colW;
  const center = (phaseIdx: number, row: number, count: number) => {
    const blockH = count * nodeH + (count - 1) * gapY;
    const y0 = top + (maxRows * (nodeH + gapY) - gapY - blockH) / 2;
    return { x: phaseIdx * colW + (colW - nodeW) / 2, y: y0 + row * (nodeH + gapY) };
  };

  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full min-w-[760px]" role="img" aria-label="Agent pipeline graph">
        <style>{`@keyframes dash { to { stroke-dashoffset: -12; } } .edge-live { stroke-dasharray: 6 4; animation: dash .8s linear infinite; }`}</style>
        {PIPELINE.map((group, pi) => (
          <text key={`h${pi}`} x={pi * colW + colW / 2} y={14} textAnchor="middle" fontSize="10" fontWeight="700" fill="#64748b" letterSpacing="0.06em">
            {group.phase}. {PHASES[pi].toUpperCase()}
          </text>
        ))}
        {/* edges: every node of phase i → every node of phase i+1 */}
        {PIPELINE.slice(0, -1).flatMap((group, pi) =>
          group.agents.flatMap((a, ai) =>
            PIPELINE[pi + 1].agents.map((b, bi) => {
              const p1 = center(pi, ai, group.agents.length);
              const p2 = center(pi + 1, bi, PIPELINE[pi + 1].agents.length);
              const live = states[a] === "done" && (states[b] === "running" || states[b] === "retrying");
              const done = states[a] === "done" && states[b] === "done";
              return (
                <line
                  key={`${a}-${b}`}
                  x1={p1.x + nodeW}
                  y1={p1.y + nodeH / 2}
                  x2={p2.x}
                  y2={p2.y + nodeH / 2}
                  stroke={live ? "#f59e0b" : done ? "#10b981" : "#1e293b"}
                  strokeWidth={live ? 2 : 1.2}
                  className={live ? "edge-live" : undefined}
                />
              );
            }),
          ),
        )}
        {PIPELINE.flatMap((group, pi) =>
          group.agents.map((agent, ai) => {
            const { x, y } = center(pi, ai, group.agents.length);
            const style = NODE_STYLE[states[agent] || "pending"];
            return (
              <g key={agent}>
                <title>{agent}</title>
                <rect x={x} y={y} width={nodeW} height={nodeH} rx="10" fill={style.fill} stroke={style.stroke} strokeWidth={states[agent] === "running" ? 2 : 1.2} />
                <text x={x + nodeW / 2} y={y + 18} textAnchor="middle" fontSize="11" fontWeight="700" fill={style.text} fontFamily="ui-monospace, monospace">
                  {shortName(agent)}
                </text>
                <text x={x + nodeW / 2} y={y + 33} textAnchor="middle" fontSize="9" fill={style.text}>
                  {style.label}
                </text>
              </g>
            );
          }),
        )}
      </svg>
    </div>
  );
}

function formatValue(v: unknown) {
  if (typeof v === "number") {
    if (Number.isInteger(v) || Math.abs(v) >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
    return v.toFixed(2);
  }
  return v == null ? "—" : String(v);
}

export default function RunPage() {
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<Status | null>(null);
  const [results, setResults] = useState<Results | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [chart, setChart] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  // Access: the share token from the link (?t=), and/or the owner's session.
  const urlShare = useSearchParams().get("t");
  const getToken = useApiToken();
  const share = urlShare || status?.share_token || null;

  const terminal = status ? TERMINAL.has(status.status) : false;

  // Poll status until the run finishes (the WebSocket makes this a fallback).
  useEffect(() => {
    if (!id || terminal) return;
    let stop = false;
    const tick = async () => {
      try {
        const s = await getStatus(id, urlShare, await getToken());
        if (stop) return;
        setStatus(s);
        setEvents((prev) => (s.events.length >= prev.length ? s.events : prev));
        setError(null);
      } catch (e) {
        if (!stop) setError(e instanceof Error ? e.message : String(e));
      }
    };
    tick();
    const t = setInterval(tick, 2500);
    return () => {
      stop = true;
      clearInterval(t);
    };
  }, [id, terminal, urlShare, getToken]);

  // Live events (the WebSocket authenticates with the share token).
  useEffect(() => {
    if (!id || !share) return;
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl(`/ws/${id}?t=${encodeURIComponent(share)}`));
      ws.onmessage = (msg) => {
        const ev = JSON.parse(msg.data) as RunEvent;
        if (ev.type === "ping") return;
        setEvents((prev) => (prev.some((p) => p.ts === ev.ts && p.type === ev.type) ? prev : [...prev, ev]));
        if (ev.type === "done" || ev.type === "error") getStatus(id, share, null).then(setStatus).catch(() => {});
      };
    } catch {
      // polling covers environments where WebSockets are blocked
    }
    return () => ws?.close();
  }, [id, share]);

  useEffect(() => {
    if (id && share && status?.status === "done" && !results)
      getResults(id, share, null).then(setResults).catch((e) => setError(String(e)));
  }, [id, share, status?.status, results]);

  const copyShareLink = async () => {
    if (!share) return;
    await navigator.clipboard.writeText(`${window.location.origin}/runs/${id}?t=${share}`);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const agentEvents = useMemo(() => events.filter((e): e is AgentEvent => e.type === "agent"), [events]);

  const states = useMemo(() => {
    const out: Record<string, NodeState> = {};
    const done = new Set([...(status?.steps_completed || []), ...agentEvents.filter((e) => e.success).map((e) => e.agent)]);
    const skipped = new Set(status?.steps_skipped || []);
    const lastByAgent = new Map(agentEvents.map((e) => [e.agent, e]));
    for (const a of ALL_AGENTS) {
      if (done.has(a)) out[a] = "done";
      else if (skipped.has(a)) out[a] = "skipped";
      else if (lastByAgent.get(a)?.success === false) out[a] = terminal ? "skipped" : "retrying";
      else out[a] = "pending";
    }
    if (!terminal && status) {
      const next = ALL_AGENTS.find((a) => out[a] === "pending");
      if (next && !Object.values(out).includes("retrying")) out[next] = "running";
    }
    return out;
  }, [status, agentEvents, terminal]);

  const phase = agentEvents.length ? agentEvents[agentEvents.length - 1].phase : status?.current_phase || 1;
  const doneCount = Object.values(states).filter((s) => s === "done").length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-mono text-xl font-bold">Run {id?.slice(0, 8)}</h1>
          <p className="text-sm text-slate-400">
            {status?.filename || "…"}
            {status?.llm ? ` • LLM: ${status.llm}` : status ? " • rule-based (no LLM key on server)" : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {share && (
            <button onClick={copyShareLink} className="rounded border border-slate-700 px-3 py-1 text-sm text-slate-300 hover:bg-slate-900" title="Anyone with this link can view the run">
              {copied ? "Link copied ✓" : "Copy share link"}
            </button>
          )}
          <span className={`rounded px-3 py-1 text-sm font-semibold ${statusBadge(status?.status || "queued")}`}>{status?.status || "connecting…"}</span>
        </div>
      </div>

      {error && !status && (
        <div className="rounded border border-red-900 bg-red-950 px-4 py-3 text-sm text-red-200">
          {/not found/i.test(error)
            ? "Run not found, or you don't have access. Open it from your History while signed in, or use its share link."
            : `Could not reach the API: ${error}. The backend may be cold-starting — this page retries automatically.`}
        </div>
      )}

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-4">
        <div className="flex gap-1.5">
          {PHASES.map((p, i) => (
            <div key={p} className={`h-2 flex-1 rounded ${i + 1 < phase || (terminal && status?.status === "done") ? "bg-emerald-500" : i + 1 === phase ? "bg-amber-500" : "bg-slate-800"}`} title={`Phase ${i + 1}: ${p}`} />
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-400">
          Phase {phase}/7 ({PHASES[phase - 1]}) • {doneCount}/{ALL_AGENTS.length} agents done
          {status?.steps_skipped?.length ? ` • ${status.steps_skipped.length} skipped` : ""} • Domain: {status?.business_domain || "detecting…"}
        </p>
        <div className="mt-4">
          <AgentGraph states={states} />
        </div>
      </section>

      {agentEvents.length > 0 && (
        <section className="rounded-xl border border-slate-800 bg-slate-950 p-4">
          <h2 className="text-sm font-semibold text-slate-300">Activity</h2>
          <ol className="mt-2 max-h-64 space-y-1 overflow-auto font-mono text-xs">
            {agentEvents.map((e, i) => (
              <li key={`${e.step}-${i}`} className={e.success ? "text-slate-300" : "text-red-300"}>
                <span className="text-slate-500">{e.duration_s.toFixed(2)}s</span>{" "}
                <span className={e.success ? "text-emerald-400" : "text-red-400"}>{e.success ? "✓" : "✗"}</span>{" "}
                <span className="font-semibold">{shortName(e.agent)}</span> — {e.message}
              </li>
            ))}
          </ol>
        </section>
      )}

      {status?.status === "failed" && (
        <div className="rounded border border-red-900 bg-red-950 p-4 text-sm text-red-200">
          <strong>Run failed:</strong> {status.error || "Unknown error"}
        </div>
      )}

      {results && (
        <div className="space-y-4">
          <section className="rounded-xl border border-emerald-800 bg-emerald-950/40 p-4">
            <h2 className="font-semibold text-emerald-200">
              Analysis complete ✓ {results.duration_s ? `in ${results.duration_s.toFixed(1)}s` : ""} • {results.business_domain} domain
              {results.evaluation && !results.evaluation.passed ? ` • quality checks flagged: ${results.evaluation.failed_checks.join(", ")}` : ""}
            </h2>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              {results.report_view_url && (
                <a href={apiUrl(results.report_view_url)} target="_blank" rel="noreferrer" className="rounded bg-emerald-600 px-3 py-1.5 text-white hover:bg-emerald-500">
                  Open full report
                </a>
              )}
              {results.report_urls.pdf && (
                <a href={apiUrl(results.report_urls.pdf)} className="rounded border border-slate-600 px-3 py-1.5 hover:bg-slate-800">Download PDF</a>
              )}
              {results.report_urls.json && (
                <a href={apiUrl(results.report_urls.json)} className="rounded border border-slate-600 px-3 py-1.5 hover:bg-slate-800">Download JSON</a>
              )}
              <span className="rounded bg-slate-800 px-3 py-1.5">
                {results.counts.kpis} KPIs • {results.counts.insights} insights • {results.counts.visualizations} charts
              </span>
            </div>
          </section>

          {results.narrative && (
            <section className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h2 className="font-semibold">Executive summary</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-200">{results.narrative.narrative}</p>
              {results.narrative.recommendations.length > 0 && (
                <>
                  <h3 className="mt-4 text-sm font-semibold text-slate-300">Recommended actions</h3>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-200">
                    {results.narrative.recommendations.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                </>
              )}
            </section>
          )}

          {results.kpis.length > 0 && (
            <section className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h2 className="font-semibold">KPIs</h2>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {results.kpis.map((k) => (
                  <div key={k.name} className="rounded border border-slate-800 bg-slate-950 p-3">
                    <div className="text-xs uppercase text-slate-400">{k.name}</div>
                    <div className="text-xl font-bold">{formatValue(k.value)}</div>
                    <div className="text-xs text-slate-500">{k.trend || "stable"}{k.formula ? ` • ${k.formula}` : ""}</div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {results.insights.length > 0 && (
            <section className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h2 className="font-semibold">Insights</h2>
              <ol className="mt-3 space-y-3 text-sm">
                {results.insights.map((ins, i) => (
                  <li key={i} className="rounded border border-slate-800 bg-slate-950 p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-slate-100">{ins.title}</span>
                      <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-300">{ins.severity}</span>
                      <span className="text-xs text-slate-500">{ins.category}{ins.confidence != null ? ` • ${Math.round(ins.confidence * 100)}%` : ""}</span>
                    </div>
                    <p className="mt-1 text-slate-300">{ins.summary}</p>
                    {ins.business_action && <p className="mt-1 text-xs text-emerald-300">Action: {ins.business_action}</p>}
                  </li>
                ))}
              </ol>
            </section>
          )}

          {results.charts.length > 0 && (
            <section className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h2 className="font-semibold">Charts</h2>
              <div className="mt-3 flex flex-wrap gap-2">
                {results.charts.map((c) => (
                  <button
                    key={c.name}
                    onClick={() => setChart(c.url)}
                    className={`rounded px-2 py-1 font-mono text-xs ${chart === c.url ? "bg-emerald-600 text-white" : "bg-slate-800 text-slate-300 hover:bg-slate-700"}`}
                  >
                    {c.name.replace(/\.html$/, "")}
                  </button>
                ))}
              </div>
              {chart && <iframe title="chart" src={apiUrl(chart)} className="mt-4 h-[480px] w-full rounded border border-slate-800 bg-white" />}
            </section>
          )}

          <section className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <h2 className="font-semibold">Execution trace</h2>
            <p className="mt-2 font-mono text-xs text-slate-400">{results.trace.steps_completed.map(shortName).join(" → ")}</p>
          </section>
        </div>
      )}

      <p className="text-xs text-slate-500">
        Run ID: {id} •{" "}
        <a href={apiUrl(`/api/status/${id}?t=${share ?? ""}`)} target="_blank" rel="noreferrer" className="underline">raw status</a> •{" "}
        <a href={apiUrl(`/api/results/${id}?t=${share ?? ""}`)} target="_blank" rel="noreferrer" className="underline">raw results</a>
      </p>
    </div>
  );
}
