"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Brief,
  Dashboard,
  KpiTile,
  RefineRequest,
  Results,
  VersionDoc,
  approve,
  getVersion,
  refine,
} from "@/lib/api";
import { useApiToken } from "@/lib/auth";

// Dark chart chrome + series/status steps from the validated reference palette (dark column).
const C = {
  series: "#3987e5",
  grid: "#2c2c2a",
  axis: "#898781",
  ink: "#f0efec",
  ink2: "#c3c2b7",
  good: "#0ca30c",
  critical: "#d03b3b",
  surface: "#1a1a19",
  // Sequential blue, light -> dark (heatmap magnitude).
  ramp: ["#184f95", "#1c5cab", "#256abf", "#2a78d6", "#3987e5", "#5598e7", "#6da7ec", "#86b6ef", "#9ec5f4"],
};

function fmt(v: number | string | null | undefined, unit?: string, compact = false): string {
  if (typeof v !== "number") return v == null ? "—" : String(v);
  const opts: Intl.NumberFormatOptions = compact
    ? { notation: "compact", maximumFractionDigits: 1 }
    : { maximumFractionDigits: Number.isInteger(v) || Math.abs(v) >= 1000 ? 0 : 2 };
  const text = v.toLocaleString(undefined, opts);
  return unit === "currency" ? `$${text}` : text;
}

function periodLabel(p: string | null | undefined): string {
  if (!p) return "";
  const m = /^(\d{4})-(\d{2})$/.exec(p);
  return m ? new Date(Number(m[1]), Number(m[2]) - 1).toLocaleString(undefined, { month: "short", year: "numeric" }) : p;
}

function Delta({ pct }: { pct: number | null | undefined }) {
  if (pct == null) return null;
  const flat = Math.abs(pct) <= 1;
  const up = pct > 0;
  return (
    <span className="text-xs font-medium" style={{ color: flat ? C.ink2 : up ? C.good : C.critical }}>
      {flat ? "■ flat" : up ? "▲ up" : "▼ down"} {Math.abs(pct).toFixed(1)}%
    </span>
  );
}

function Sparkline({ values }: { values: (number | null)[] }) {
  const data = values.map((v, i) => ({ i, v }));
  return (
    <div className="h-10 w-full" aria-hidden>
      <ResponsiveContainer>
        <LineChart data={data} margin={{ top: 4, right: 2, bottom: 2, left: 2 }}>
          <Line type="monotone" dataKey="v" stroke={C.series} strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function KpiTiles({ tiles, period }: { tiles: KpiTile[]; period: Dashboard["period"] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {tiles.map((t) => (
        <div key={t.key} className="rounded-lg border border-white/10 p-4" style={{ background: C.surface }}>
          <div className="text-xs uppercase tracking-wide" style={{ color: C.ink2 }}>{t.label}</div>
          <div className="mt-1 text-2xl font-semibold" style={{ color: C.ink }}>{fmt(t.value, t.unit)}</div>
          {t.change_pct !== undefined && (
            <div className="mt-1 flex flex-wrap items-baseline gap-x-2">
              <Delta pct={t.change_pct} />
              <span className="text-xs" style={{ color: C.axis }}>
                {periodLabel(period.current)}: {fmt(t.current, t.unit)} vs {fmt(t.previous, t.unit)}
              </span>
            </div>
          )}
          {t.spark && t.spark.length > 1 && <Sparkline values={t.spark} />}
        </div>
      ))}
    </div>
  );
}

const PRIORITY: Record<string, string> = {
  high: "bg-red-950 text-red-200 border-red-900",
  medium: "bg-amber-950 text-amber-200 border-amber-900",
  low: "bg-slate-800 text-slate-300 border-slate-700",
};

function BriefPanel({ brief }: { brief: Brief }) {
  return (
    <section className="rounded-xl border border-white/10 p-5" style={{ background: C.surface }}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold" style={{ color: C.ink }}>{brief.headline}</h2>
        <span className="rounded border border-white/10 px-2 py-0.5 text-xs" style={{ color: C.ink2 }}>
          {brief.source === "llm" ? "AI-written · numbers verified" : "Rule-based"}
        </span>
      </div>
      <p className="mt-2 text-sm leading-relaxed" style={{ color: C.ink2 }}>{brief.summary}</p>
      <div className="mt-4 grid gap-5 lg:grid-cols-2">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide" style={{ color: C.axis }}>Key findings</h3>
          <ul className="mt-2 space-y-2">
            {brief.findings.map((f, i) => (
              <li key={i} className="text-sm">
                <span style={{ color: f.direction === "up" ? C.good : f.direction === "down" ? C.critical : C.ink2 }}>
                  {f.direction === "up" ? "▲" : f.direction === "down" ? "▼" : "■"}
                </span>{" "}
                <span className="font-medium" style={{ color: C.ink }}>{f.title}</span>
                <div className="text-xs" style={{ color: C.ink2 }}>{f.so_what}</div>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wide" style={{ color: C.axis }}>Recommended actions</h3>
          <ol className="mt-2 space-y-2">
            {brief.recommendations.map((r, i) => (
              <li key={i} className="text-sm">
                <span className={`mr-2 rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase ${PRIORITY[r.priority]}`}>{r.priority}</span>
                <span className="font-medium" style={{ color: C.ink }}>{r.action}</span>
                <div className="text-xs" style={{ color: C.ink2 }}>{r.rationale}</div>
              </li>
            ))}
          </ol>
          {brief.risks.length > 0 && (
            <>
              <h3 className="mt-4 text-xs font-semibold uppercase tracking-wide" style={{ color: C.axis }}>Risks & caveats</h3>
              <ul className="mt-1 list-disc pl-5 text-xs" style={{ color: C.ink2 }}>
                {brief.risks.map((r) => <li key={r}>{r}</li>)}
              </ul>
            </>
          )}
        </div>
      </div>
    </section>
  );
}

const tooltipStyle = {
  contentStyle: { background: "#0d0d0d", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 6, color: C.ink, fontSize: 12 },
  labelStyle: { color: C.ink2 },
  cursor: { stroke: C.axis, strokeDasharray: "3 3" },
};

function TrendChart({ dash }: { dash: Dashboard }) {
  const metrics = dash.kpis.filter((k) => dash.trend.length && k.key in dash.trend[0]);
  const [metric, setMetric] = useState(metrics[0]?.key ?? "");
  const tile = metrics.find((k) => k.key === metric);
  if (!dash.trend.length || !tile) return null;
  return (
    <section className="rounded-xl border border-white/10 p-4" style={{ background: C.surface }}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold" style={{ color: C.ink }}>{tile.label} by {dash.period.grain}</h3>
        <div className="flex gap-1" role="tablist">
          {metrics.map((k) => (
            <button key={k.key} role="tab" aria-selected={k.key === metric} onClick={() => setMetric(k.key)}
              className={`rounded px-2 py-1 text-xs ${k.key === metric ? "bg-white/10 text-white" : "text-slate-400 hover:text-white"}`}>
              {k.label}
            </button>
          ))}
        </div>
      </div>
      <div className="mt-3 h-64">
        <ResponsiveContainer>
          <LineChart data={dash.trend} margin={{ top: 8, right: 16, bottom: 4, left: 8 }}>
            <CartesianGrid stroke={C.grid} vertical={false} />
            <XAxis dataKey="period" tickFormatter={periodLabel} stroke={C.axis} tick={{ fontSize: 11 }} tickLine={false} />
            <YAxis tickFormatter={(v) => fmt(v, tile.unit, true)} stroke={C.axis} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} width={64} />
            <Tooltip {...tooltipStyle} labelFormatter={(p) => periodLabel(String(p))} formatter={(v) => [fmt(Number(v), tile.unit), tile.label]} />
            <Line type="monotone" dataKey={metric} stroke={C.series} strokeWidth={2} dot={{ r: 3, strokeWidth: 0, fill: C.series }} activeDot={{ r: 5, stroke: C.surface, strokeWidth: 2 }} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function BreakdownChart({ b, unit }: { b: Dashboard["breakdowns"][number]; unit: string }) {
  const height = Math.max(140, b.rows.length * 30 + 30);
  return (
    <section className="rounded-xl border border-white/10 p-4" style={{ background: C.surface }}>
      <h3 className="font-semibold" style={{ color: C.ink }}>
        {b.metric === "revenue" ? "Revenue" : "Records"} by {b.dimension.replace(/_/g, " ")}
      </h3>
      <div className="mt-2" style={{ height }}>
        <ResponsiveContainer>
          <BarChart data={b.rows} layout="vertical" margin={{ top: 4, right: 56, bottom: 4, left: 4 }} barCategoryGap={4}>
            <XAxis type="number" hide />
            <YAxis type="category" dataKey="name" width={96} stroke={C.axis} tick={{ fontSize: 11, fill: C.ink2 }} tickLine={false} axisLine={false} />
            <Tooltip {...tooltipStyle} cursor={{ fill: "rgba(255,255,255,0.04)" }}
              formatter={(v, _n, item) => [`${fmt(Number(v), unit)} (${item.payload.share_pct}%)`, b.metric === "revenue" ? "Revenue" : "Records"]} />
            <Bar dataKey="value" fill={C.series} radius={[0, 4, 4, 0]} isAnimationActive={false}
              label={{ position: "right", fill: C.ink2, fontSize: 11, formatter: (v: unknown) => fmt(Number(v), unit, true) }} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function TopItems({ dash }: { dash: Dashboard }) {
  const t = dash.top_items;
  if (!t?.rows.length) return null;
  const cols = ["revenue", "orders", "units", "aov"].filter((c) => c in t.rows[0]);
  const labels: Record<string, string> = { revenue: "Revenue", orders: "Orders", units: "Units", aov: "Avg order" };
  return (
    <section className="rounded-xl border border-white/10 p-4" style={{ background: C.surface }}>
      <h3 className="font-semibold" style={{ color: C.ink }}>Top 10 by revenue — {t.dimension.replace(/_/g, " ")}</h3>
      <table className="mt-2 w-full text-sm" style={{ fontVariantNumeric: "tabular-nums" }}>
        <thead>
          <tr className="text-left text-xs uppercase" style={{ color: C.axis }}>
            <th className="py-1 font-medium">#</th>
            <th className="py-1 font-medium">{t.dimension.replace(/_/g, " ")}</th>
            {cols.map((c) => <th key={c} className="py-1 text-right font-medium">{labels[c]}</th>)}
          </tr>
        </thead>
        <tbody>
          {t.rows.map((r, i) => (
            <tr key={String(r.name)} className="border-t border-white/5" style={{ color: C.ink2 }}>
              <td className="py-1.5" style={{ color: C.axis }}>{i + 1}</td>
              <td className="py-1.5" style={{ color: C.ink }}>{String(r.name)}</td>
              {cols.map((c) => (
                <td key={c} className="py-1.5 text-right">{fmt(r[c] as number, c === "revenue" || c === "aov" ? "currency" : "count")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Heatmap({ dash }: { dash: Dashboard }) {
  const hm = dash.heatmap;
  const [hover, setHover] = useState<string | null>(null);
  if (!hm) return null;
  const max = Math.max(...hm.cells.map((c) => c.value || 0), 1);
  const cell = new Map(hm.cells.map((c) => [`${c.day}-${c.hour}`, c.value]));
  const unit = hm.metric === "revenue" ? "currency" : "count";
  return (
    <section className="rounded-xl border border-white/10 p-4" style={{ background: C.surface }}>
      <div className="flex items-center justify-between">
        <h3 className="font-semibold" style={{ color: C.ink }}>When demand peaks (day × hour)</h3>
        <span className="text-xs" style={{ color: C.ink2 }}>{hover ?? "Hover a cell"}</span>
      </div>
      <div className="mt-3 overflow-x-auto">
        <div className="grid gap-[2px]" style={{ gridTemplateColumns: `40px repeat(${hm.hours.length}, minmax(22px, 1fr))` }}>
          <div />
          {hm.hours.map((h) => <div key={h} className="text-center text-[10px]" style={{ color: C.axis }}>{h}</div>)}
          {hm.days.map((d) => (
            <div key={d} className="contents">
              <div className="pr-1 text-right text-[11px] leading-6" style={{ color: C.ink2 }}>{d}</div>
              {hm.hours.map((h) => {
                const v = cell.get(`${d}-${h}`) ?? 0;
                const step = v ? Math.min(C.ramp.length - 1, Math.floor((v / max) * C.ramp.length)) : -1;
                return (
                  <div key={h} className="h-6 rounded-[3px]"
                    style={{ background: step < 0 ? "#222220" : C.ramp[step] }}
                    onMouseEnter={() => setHover(`${d} ${h}:00 — ${fmt(v, unit)}`)}
                    onMouseLeave={() => setHover(null)}
                    title={`${d} ${h}:00 — ${fmt(v, unit)}`} />
                );
              })}
            </div>
          ))}
        </div>
        <div className="mt-2 flex items-center gap-2 text-[10px]" style={{ color: C.axis }}>
          <span>Low</span>
          <div className="flex">{C.ramp.map((c) => <span key={c} className="h-2 w-5" style={{ background: c }} />)}</div>
          <span>High</span>
        </div>
      </div>
    </section>
  );
}

function RefinePanel({ dash, llmAvailable, busy, onApply }: {
  dash: Dashboard; llmAvailable: boolean; busy: boolean; onApply: (body: RefineRequest) => void;
}) {
  const spec = dash.version_spec;
  const opts = dash.options;
  const [kpis, setKpis] = useState<string[]>(spec.kpis);
  const [dims, setDims] = useState<string[]>(spec.dimensions);
  const [grain, setGrain] = useState<string | null>(spec.grain);
  const [filters, setFilters] = useState<Record<string, string[]>>(spec.filters);
  const [text, setText] = useState("");
  const toggle = (list: string[], v: string) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);
  const kpiLabel = Object.fromEntries(dash.kpis.map((k) => [k.key, k.label]));

  return (
    <section className="space-y-4 rounded-xl border border-emerald-900 bg-emerald-950/20 p-4">
      <h3 className="font-semibold text-emerald-200">Refine this dashboard</h3>
      <div className="grid gap-4 md:grid-cols-3">
        <fieldset>
          <legend className="text-xs uppercase text-slate-400">KPIs</legend>
          {opts.kpis.map((k) => (
            <label key={k} className="mt-1 flex items-center gap-2 text-sm text-slate-200">
              <input type="checkbox" checked={kpis.includes(k)} onChange={() => setKpis(toggle(kpis, k))} /> {kpiLabel[k] ?? k}
            </label>
          ))}
        </fieldset>
        <fieldset>
          <legend className="text-xs uppercase text-slate-400">Break down by</legend>
          {opts.dimensions.map((d) => (
            <label key={d} className="mt-1 flex items-center gap-2 text-sm text-slate-200">
              <input type="checkbox" checked={dims.includes(d)} onChange={() => setDims(toggle(dims, d))} /> {d}
            </label>
          ))}
        </fieldset>
        <div>
          {opts.grains.length > 0 && (
            <label className="block text-xs uppercase text-slate-400">
              Time grain
              <select value={grain ?? ""} onChange={(e) => setGrain(e.target.value || null)}
                className="mt-1 block w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm normal-case text-slate-200">
                {opts.grains.map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
            </label>
          )}
          {Object.entries(opts.filters).map(([k, values]) => (
            <label key={k} className="mt-2 block text-xs uppercase text-slate-400">
              Filter: {k.replace(/_/g, " ")}
              <select multiple value={filters[k] ?? []} size={Math.min(4, values.length)}
                onChange={(e) => setFilters({ ...filters, [k]: Array.from(e.target.selectedOptions, (o) => o.value) })}
                className="mt-1 block w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm normal-case text-slate-200">
                {values.map((v) => <option key={v} value={v}>{v}</option>)}
              </select>
            </label>
          ))}
        </div>
      </div>
      <label className="block text-xs uppercase text-slate-400">
        Or describe what you want to see
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2} disabled={!llmAvailable}
          placeholder={llmAvailable ? "e.g. Focus on weekend sales by pizza size, monthly" : "Needs an LLM key on the server — use the controls above"}
          className="mt-1 block w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm normal-case text-slate-200 disabled:opacity-50" />
      </label>
      <button disabled={busy || !kpis.length} onClick={() => onApply({ kpis, dimensions: dims, grain, filters, instructions: text || undefined })}
        className="rounded bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:opacity-50">
        {busy ? "Building new version…" : "Create new version"}
      </button>
    </section>
  );
}

export default function ExecutiveDashboard({ runId, results, share, isOwner }: {
  runId: string; results: Results; share: string | null; isOwner: boolean;
}) {
  const getToken = useApiToken();
  const latest = results.versions.at(-1)?.version ?? 1;
  const [versions, setVersions] = useState(results.versions);
  const [current, setCurrent] = useState<number>(latest);
  const [doc, setDoc] = useState<VersionDoc | null>(null);
  const [approved, setApproved] = useState<number | null>(results.approved_version);
  const [refining, setRefining] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getVersion(runId, current, share, null).then(setDoc).catch((e) => setError(String(e)));
  }, [runId, current, share]);

  const unit = useMemo(() => doc?.dashboard.kpis[0]?.unit ?? "count", [doc]);
  if (!doc) return <div className="text-sm text-slate-400">{error ?? "Loading dashboard…"}</div>;
  const dash = doc.dashboard;

  const onApply = async (body: RefineRequest) => {
    setBusy(true);
    setError(null);
    try {
      const v = await refine(runId, body, getToken);
      setVersions([...versions, { version: v.version, kind: v.kind, created_at: v.created_at, instructions: v.instructions, headline: v.brief.headline, spec: v.dashboard.version_spec }]);
      setDoc(v);
      setCurrent(v.version);
      setRefining(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const onApprove = async () => {
    setBusy(true);
    try {
      setApproved((await approve(runId, current, getToken)).approved_version);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const filtersText = Object.entries(dash.version_spec.filters).map(([k, v]) => `${k}: ${v.join(", ")}`).join(" · ");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm text-slate-400">
          {dash.date_range ? `${dash.date_range[0]} → ${dash.date_range[1]}` : "No date column"} · {dash.rows_in_view.toLocaleString()} rows
          {filtersText && ` · ${filtersText}`}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {versions.length > 1 && (
            <select value={current} onChange={(e) => setCurrent(Number(e.target.value))}
              className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-200" aria-label="Dashboard version">
              {versions.map((v) => (
                <option key={v.version} value={v.version}>
                  v{v.version} {v.kind === "original" ? "(original)" : v.instructions ? `— ${v.instructions.slice(0, 40)}` : "(refined)"}
                  {approved === v.version ? " ✓" : ""}
                </option>
              ))}
            </select>
          )}
          {approved === current && <span className="rounded bg-emerald-600 px-2 py-1 text-xs font-semibold text-white">✓ Approved</span>}
        </div>
      </div>

      {isOwner && approved !== current && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-700 bg-slate-900 p-4">
          <span className="text-sm text-slate-200">Does this dashboard look right?</span>
          <div className="flex gap-2">
            <button onClick={onApprove} disabled={busy} className="rounded bg-emerald-500 px-4 py-1.5 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:opacity-50">
              Yes, approve v{current}
            </button>
            <button onClick={() => setRefining(!refining)} className="rounded border border-slate-600 px-4 py-1.5 text-sm text-slate-200 hover:bg-slate-800">
              {refining ? "Close" : "Refine…"}
            </button>
          </div>
        </div>
      )}
      {error && <div className="rounded border border-red-900 bg-red-950 px-4 py-2 text-sm text-red-200">{error}</div>}
      {refining && <RefinePanel key={`refine-${current}`} dash={dash} llmAvailable={results.llm_available} busy={busy} onApply={onApply} />}

      <KpiTiles tiles={dash.kpis} period={dash.period} />
      {doc.brief && <BriefPanel brief={doc.brief} />}
      <TrendChart key={`trend-${current}`} dash={dash} />
      <div className="grid gap-4 lg:grid-cols-2">
        {dash.breakdowns.map((b) => <BreakdownChart key={b.dimension} b={b} unit={unit} />)}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <TopItems dash={dash} />
        <Heatmap dash={dash} />
      </div>
    </div>
  );
}
