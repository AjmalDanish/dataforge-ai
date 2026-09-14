import Link from "next/link";

const SAMPLES = [
  { name: "employees.csv", rows: "15 × 8", hint: "HR • turnover / salary equity" },
  { name: "products.csv", rows: "20 × 8", hint: "Retail • product / revenue" },
];

export default function HomePage() {
  return (
    <div className="space-y-12">
      <section className="rounded-2xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-8">
        <p className="text-xs uppercase tracking-widest text-emerald-400">Autonomous Business Intelligence Engineer</p>
        <h1 className="mt-2 text-4xl font-bold tracking-tight">
          Upload data, get the answers a <span className="text-emerald-400">Senior Analyst</span> would give.
        </h1>
        <p className="mt-3 max-w-2xl text-slate-300">
          DataForge runs a 13-agent LangGraph — validation → cleaning → schema → domain → KPI → insights → dashboard →
          executive report. No config, no prompts. Built to prove Data Scientist / ML engineering depth.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link href="/upload" className="rounded bg-emerald-500 px-5 py-2.5 font-semibold text-slate-950 hover:bg-emerald-400">
            Try live demo →
          </Link>
          <Link href="/history" className="rounded border border-slate-700 px-5 py-2.5 text-slate-200 hover:bg-slate-900">
            View history
          </Link>
        </div>
        <p className="mt-3 text-xs text-slate-500">Backend on HuggingFace Spaces may cold-start ~30s. Upload is free and private.</p>
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="font-semibold">How it works</h2>
          <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-slate-300">
            <li>Upload CSV / XLSX / Parquet / JSON (≤100 MB, ≤1M rows)</li>
            <li>Watch 13 agents live — validation through executive report</li>
            <li>Get KPI cards, ranked insights, dashboard, HTML/JSON report + share link</li>
          </ol>
          <p className="mt-3 text-xs text-slate-500">Every cleaning decision is logged and explained. Skipped agents are audited.</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="font-semibold">Try a sample</h2>
          <div className="mt-3 space-y-2">
            {SAMPLES.map((s) => (
              <div key={s.name} className="flex items-center justify-between rounded border border-slate-800 bg-slate-950 px-4 py-3">
                <div>
                  <div className="font-mono text-sm">{s.name}</div>
                  <div className="text-xs text-slate-400">{s.rows} • {s.hint}</div>
                </div>
                <Link href="/upload" className="text-sm text-emerald-400 hover:text-emerald-300">Use →</Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="font-semibold">Architecture</h2>
        <p className="mt-2 font-mono text-xs text-slate-400 break-all">
          Next.js + Tailwind @ Netlify → FastAPI @ HuggingFace Spaces → LangGraph 13 agents → Neon Postgres (runs, events, KPIs, insights, checkpoints)
        </p>
        <p className="mt-2 text-sm text-slate-300">Single repo, single main branch — docs cover PRD → TRD → UI/UX → Database (docs/PRD.md etc.).</p>
      </section>
    </div>
  );
}
