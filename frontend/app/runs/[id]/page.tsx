"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { API_URL, getResults, getStatus, wsUrl } from "@/lib/api";

const PHASES = ["Intake", "Prep", "Understand", "Deep", "Stats", "Synthesis", "Output"];
// 12 agents in pipeline order, grouped by phase for the DAG
const PIPELINE: { phase: number; agents: string[] }[] = [
  { phase: 1, agents: ["DataValidationAgent"] },
  { phase: 2, agents: ["DataCleaningAgent"] },
  { phase: 3, agents: ["SchemaDetectionAgent", "BusinessDomainDetectionAgent", "BusinessObjectiveDetectionAgent"] },
  { phase: 4, agents: ["DataProfilingAgent", "FeatureEngineeringAgent", "KPIDiscoveryAgent"] },
  { phase: 5, agents: ["StatisticalAnalysisAgent"] },
  { phase: 6, agents: ["InsightGenerationAgent"] },
  { phase: 7, agents: ["VisualizationAgent", "ReportingAgent"] },
];
const FLAT_AGENTS = PIPELINE.flatMap((p) => p.agents);

function shortName(a: string) {
  return a.replace("Agent", "").replace("Data", "").replace("Business", "");
}
function badge(status: string) {
  const m: Record<string, string> = {
    queued: "bg-slate-700",
    running: "bg-amber-500 text-slate-950 animate-pulse",
    done: "bg-emerald-500 text-slate-950",
    failed: "bg-red-600",
  };
  return m[status] || "bg-slate-700";
}

function AgentDAG({ steps, status: runStatus, stepsSkipped }: { steps: string[]; status: string; stepsSkipped: string[] }) {
  const doneSet = new Set(steps);
  const skippedSet = new Set(stepsSkipped || []);
  // first not-done, not-skipped is "running" when pipeline is running
  const nextAgent = FLAT_AGENTS.find((a) => !doneSet.has(a) && !skippedSet.has(a)) || null;
  const isRunning = runStatus === "running" || runStatus === "queued";

  // layout: 12 nodes in a single wrapped row for desktop, vertical for mobile is handled via viewBox + flex fallback
  // SVG horizontal DAG: one row, arrows between consecutive agents, phases as background bands
  const nodeW = 110;
  const nodeH = 48;
  const gapX = 32;
  const padX = 16;
  const totalW = padX * 2 + FLAT_AGENTS.length * nodeW + (FLAT_AGENTS.length - 1) * gapX;
  const totalH = 96;

  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${totalW} ${totalH + 28}`} className="h-[124px] w-full min-w-[720px]" role="img" aria-label="Agent DAG">
        <defs>
          <marker id="arrow-done" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L8,3 z" fill="#10b981" />
          </marker>
          <marker id="arrow-pending" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#334155" />
          </marker>
          <marker id="arrow-running" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#f59e0b" />
          </marker>
          <style>{`@keyframes dash { to { stroke-dashoffset: -12; } } .edge-running { stroke-dasharray: 6 4; animation: dash 0.8s linear infinite; }`}</style>
        </defs>

        {/* phase bands */}
        {PIPELINE.map((group) => {
          const firstIdx = FLAT_AGENTS.indexOf(group.agents[0]);
          const lastIdx = FLAT_AGENTS.indexOf(group.agents[group.agents.length - 1]);
          const x = padX + firstIdx * (nodeW + gapX) - 6;
          const w = (lastIdx - firstIdx + 1) * nodeW + (lastIdx - firstIdx) * gapX + 12;
          const isActive = group.phase <= (doneSet.size ? Math.max(1, Math.ceil((doneSet.size / FLAT_AGENTS.length) * 7)) : 1);
          return (
            <g key={group.phase}>
              <rect x={x} y="22" width={w} height={totalH - 4} rx="10" fill={isActive ? "#0f172a" : "#020617"} stroke={isActive ? "#1e293b" : "#0f172a"} />
              <text x={x + 8} y="18" fontSize="9" fill="#64748b" fontWeight="700" letterSpacing="0.06em">
                {group.phase}. {PHASES[group.phase - 1].toUpperCase()}
              </text>
            </g>
          );
        })}

        {/* edges */}
        {FLAT_AGENTS.slice(0, -1).map((_, i) => {
          const a = FLAT_AGENTS[i];
          const b = FLAT_AGENTS[i + 1];
          const aDone = doneSet.has(a);
          const bDone = doneSet.has(b);
          const isRunningEdge = isRunning && aDone && b === nextAgent;
          const x1 = padX + i * (nodeW + gapX) + nodeW;
          const x2 = padX + (i + 1) * (nodeW + gapX);
          const y = 22 + totalH / 2;
          const stroke = isRunningEdge ? "#f59e0b" : bDone || aDone ? "#10b981" : "#334155";
          const marker = isRunningEdge ? "url(#arrow-running)" : bDone || aDone ? "url(#arrow-done)" : "url(#arrow-pending)";
          return (
            <line
              key={`e-${i}`}
              x1={x1}
              y1={y}
              x2={x2 - 4}
              y2={y}
              stroke={stroke}
              strokeWidth={isRunningEdge ? 2.5 : 1.8}
              markerEnd={marker}
              className={isRunningEdge ? "edge-running" : undefined}
              opacity={isRunningEdge ? 1 : aDone ? 1 : 0.6}
            />
          );
        })}

        {/* nodes */}
        {FLAT_AGENTS.map((agent, i) => {
          const isDone = doneSet.has(agent);
          const isSkipped = skippedSet.has(agent);
          const isNext = agent === nextAgent && isRunning;
          const x = padX + i * (nodeW + gapX);
          const y = 22 + (totalH - nodeH) / 2;
          let fill = "#0f172a";
          let stroke = "#334155";
          let textColor = "#94a3b8";
          if (isDone) {
            fill = "#064e3b";
            stroke = "#10b981";
            textColor = "#a7f3d0";
          } else if (isNext) {
            fill = "#78350f";
            stroke = "#f59e0b";
            textColor = "#fde68a";
          } else if (isSkipped) {
            fill = "#1e293b";
            stroke = "#475569";
            textColor = "#64748b";
          }
          const label = shortName(agent);
          const sub = isDone ? "✓ done" : isSkipped ? "⊘ skipped" : isNext ? "● running" : "… pending";
          return (
            <g key={agent}>
              <rect x={x} y={y} width={nodeW} height={nodeH} rx="10" fill={fill} stroke={stroke} strokeWidth={isNext ? 2 : 1.2} />
              {isNext && <rect x={x} y={y} width={nodeW} height={nodeH} rx="10" fill="none" stroke="#f59e0b" strokeWidth="1" opacity="0.35" className="animate-pulse" />}
              <text x={x + nodeW / 2} y={y + 18} textAnchor="middle" fontSize="10" fontWeight="700" fill={textColor} fontFamily="ui-monospace, SFMono-Regular, monospace">
                {label}
              </text>
              <text x={x + nodeW / 2} y={y + 32} textAnchor="middle" fontSize="9" fill={textColor} opacity={0.9}>
                {sub}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="mt-2 text-xs text-slate-500">
        Pipeline: {FLAT_AGENTS.map((a) => shortName(a)).join(" → ")} •{" "}
        <span className="text-emerald-400">green = done</span>, <span className="text-amber-400">amber pulse = running</span>, slate = pending
      </p>
    </div>
  );
}

export default function RunPage() {
  const { id } = useParams<{ id: string }>();
  const [status, setStatus] = useState<any>(null);
  const [results, setResults] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!id) return;
    let t: any;
    const poll = async () => {
      try {
        const s = await getStatus(id);
        setStatus(s);
        setEvents(s.events || []);
        if (s.status === "done" || s.status === "failed") {
          try {
            const r = await getResults(id);
            setResults(r);
          } catch {}
        }
      } catch {}
      if (!status || (status.status !== "done" && status.status !== "failed")) {
        t = setTimeout(poll, 1800);
      }
    };
    poll();
    return () => clearTimeout(t);
  }, [id, status?.status]);

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
            if (msg.steps_completed) setStatus((s: any) => (s ? { ...s, steps_completed: msg.steps_completed, current_phase: msg.current_phase } : s));
            if (msg.type === "done" || msg.type === "error") {
              getResults(id).then(setResults).catch(() => {});
              getStatus(id).then(setStatus).catch(() => {});
            }
          }
        } catch {}
      };
      return () => {
        try {
          ws.close();
        } catch {}
      };
    } catch {}
  }, [id]);

  const done = status?.status === "done";
  const failed = status?.status === "failed";
  const steps: string[] = status?.steps_completed || [];
  const stepsSkipped: string[] = status?.steps_skipped || [];
  const phase = status?.current_phase || 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-mono text-xl font-bold">Run {id?.slice(0, 8)}</h1>
        <span className={`rounded px-3 py-1 text-sm font-semibold ${badge(status?.status || "queued")}`}>{status?.status || "…"}</span>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
        <div className="flex gap-1.5">
          {PHASES.map((p, i) => (
            <div key={p} className={`h-2 flex-1 rounded ${i + 1 <= phase ? "bg-emerald-500" : "bg-slate-800"}`} title={`Phase ${i + 1}: ${p}`} />
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-400">
          Phase {phase} / 7 • {steps.length} agents done {stepsSkipped.length ? `• ${stepsSkipped.length} skipped` : ""} • Domain: {status?.business_domain || "detecting…"}
        </p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Agent graph (live)</h2>
          <span className="text-xs text-slate-400">12 agents • 7 phases • arrows animate while running</span>
        </div>
        <div className="mt-4">
          <AgentDAG steps={steps} status={status?.status || "queued"} stepsSkipped={stepsSkipped} />
        </div>
        {/* detailed grid for quick scan + a11y */}
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
          {FLAT_AGENTS.map((a) => {
            const isDone = steps.includes(a);
            const isSkipped = stepsSkipped.includes(a);
            const isNext = !isDone && !isSkipped && a === FLAT_AGENTS.find((x) => !steps.includes(x) && !stepsSkipped.includes(x)) && (status?.status === "running" || status?.status === "queued");
            const short = shortName(a);
            return (
              <div
                key={a}
                className={`rounded border px-3 py-2 text-xs ${
                  isDone
                    ? "border-emerald-700 bg-emerald-950 text-emerald-200"
                    : isNext
                      ? "border-amber-600 bg-amber-950 text-amber-200 animate-pulse"
                      : isSkipped
                        ? "border-slate-700 bg-slate-900 text-slate-500"
                        : "border-slate-800 bg-slate-950 text-slate-400"
                }`}
              >
                <div className="truncate font-mono" title={a}>
                  {short}
                </div>
                <div>{isDone ? "✓ done" : isSkipped ? "⊘ skipped" : isNext ? "● running" : "… pending"}</div>
              </div>
            );
          })}
        </div>
        <p className="mt-3 text-xs text-slate-500">Live via WebSocket {API_URL.replace("http", "ws")}/ws/{id} • polling every 1.8s • DAG edges pulse amber while the pipeline is running</p>
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
              {results.report_urls?.html && (
                <a href={`${API_URL}${results.report_urls.html}`} target="_blank" className="rounded bg-emerald-600 px-3 py-1.5 text-white hover:bg-emerald-500">
                  Open HTML report
                </a>
              )}
              {results.report_urls?.json && (
                <a href={`${API_URL}${results.report_urls.json}`} target="_blank" className="rounded border border-slate-600 px-3 py-1.5 hover:bg-slate-800">
                  Download JSON
                </a>
              )}
              <span className="rounded bg-slate-800 px-3 py-1.5">
                {results.counts?.kpis ?? 0} KPIs • {results.counts?.insights ?? 0} insights • {results.counts?.visualizations ?? 0} viz
              </span>
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
                  <li key={i}>
                    <span className="font-semibold">{ins.title || ins.category}</span> — {ins.summary || ins.business_action || ""}{" "}
                    <span className="text-xs text-slate-500">
                      ({ins.severity}, {Math.round((ins.confidence || 0) * 100)}%)
                    </span>
                  </li>
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

      <p className="text-xs text-slate-500">
        Run ID: {id} • <a href={`${API_URL}/api/status/${id}`} target="_blank" className="underline">raw status</a> •{" "}
        <a href={`${API_URL}/api/results/${id}`} target="_blank" className="underline">
          raw results
        </a>
      </p>
    </div>
  );
}
