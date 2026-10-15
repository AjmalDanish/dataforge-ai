"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Status, getHistory } from "@/lib/api";
import { SignInPrompt, useApiToken, useSignedIn } from "@/lib/auth";

export default function HistoryPage() {
  const getToken = useApiToken();
  const signedIn = useSignedIn();
  const [runs, setRuns] = useState<Status[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!signedIn) return;
    getToken()
      .then((token) => getHistory(token, 50))
      .then((j) => setRuns(j.runs || []))
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, [signedIn, getToken]);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Your runs</h1>
      {signedIn === false && <SignInPrompt message="Sign in to see the analyses you've run. History is private to your account." />}
      {err && <div className="rounded border border-red-900 bg-red-950 px-4 py-3 text-sm text-red-200">{err}</div>}
      {signedIn && (
        <div className="overflow-x-auto rounded border border-slate-800">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900 text-slate-400">
              <tr><th className="px-4 py-2">Run</th><th className="px-4 py-2">File</th><th className="px-4 py-2">Status</th><th className="px-4 py-2">Domain</th><th className="px-4 py-2">Duration</th><th className="px-4 py-2">Started</th></tr>
            </thead>
            <tbody>
              {(runs || []).map((r) => (
                <tr key={r.run_id} className="border-t border-slate-800 hover:bg-slate-900">
                  <td className="px-4 py-2 font-mono text-xs">
                    <Link href={`/runs/${r.run_id}?t=${r.share_token}`} className="text-emerald-400 hover:underline">{r.run_id.slice(0, 8)}</Link>
                  </td>
                  <td className="px-4 py-2">{r.filename || "—"}</td>
                  <td className="px-4 py-2">{r.status}</td>
                  <td className="px-4 py-2">{r.business_domain || "—"}</td>
                  <td className="px-4 py-2">{r.duration_s ? `${r.duration_s.toFixed(1)}s` : "—"}</td>
                  <td className="px-4 py-2 text-slate-400">{new Date(r.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {runs === null && !err && <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">Loading…</td></tr>}
              {runs?.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-500">No runs yet — upload a dataset or try a sample.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-xs text-slate-500">Runs are stored on the API server and may be cleared when it restarts.</p>
    </div>
  );
}
