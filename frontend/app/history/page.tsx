"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { API_URL, getHistory } from "@/lib/api";

export default function HistoryPage() {
  const [runs, setRuns] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getHistory(50)
      .then((j) => setRuns(j.runs || []))
      .catch((e) => setErr(String(e)));
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">History</h1>
      <p className="text-sm text-slate-400">Recent runs on {API_URL} • Private to this backend volume (resets on redeploy in MVP)</p>
      {err && <div className="rounded border border-red-900 bg-red-950 px-4 py-3 text-sm text-red-200">{err}</div>}
      <div className="overflow-x-auto rounded border border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr><th className="px-4 py-2">Run</th><th className="px-4 py-2">File</th><th className="px-4 py-2">Status</th><th className="px-4 py-2">Domain</th><th className="px-4 py-2">Duration</th></tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.run_id} className="border-t border-slate-800 hover:bg-slate-900">
                <td className="px-4 py-2 font-mono text-xs"><Link href={`/runs/${r.run_id}`} className="text-emerald-400 hover:underline">{r.run_id.slice(0, 8)}</Link></td>
                <td className="px-4 py-2">{r.filename || "—"}</td>
                <td className="px-4 py-2">{r.status}</td>
                <td className="px-4 py-2">{r.business_domain || "—"}</td>
                <td className="px-4 py-2">{r.duration_s ? `${r.duration_s.toFixed(1)}s` : "—"}</td>
              </tr>
            ))}
            {runs.length === 0 && !err && <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-500">No runs yet — head to Upload</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
