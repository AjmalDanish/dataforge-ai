"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { API_URL, analyze } from "@/lib/api";

const ACCEPT = ".csv,.xlsx,.xls,.parquet,.pq,.json";
const MAX_MB = 100;

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onFile = useCallback((f: File | null) => {
    setError(null);
    if (!f) { setFile(null); return; }
    const ext = "." + (f.name.split(".").pop() || "").toLowerCase();
    const ok = [".csv", ".xlsx", ".xls", ".parquet", ".pq", ".json"].includes(ext);
    if (!ok) { setError(`Unsupported format ${ext}. Allowed: ${ACCEPT}`); return; }
    if (f.size > MAX_MB * 1024 * 1024) { setError(`File too large — max ${MAX_MB} MB`); return; }
    setFile(f);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0] || null;
    onFile(f);
  }, [onFile]);

  const submit = useCallback(async () => {
    if (!file) { setError("Choose a file first"); return; }
    setBusy(true);
    setError(null);
    try {
      const res = await analyze(file);
      router.push(`/runs/${res.run_id}`);
    } catch (e: any) {
      setError(e?.message || String(e));
      setBusy(false);
    }
  }, [file, router]);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">Upload dataset</h1>
      <p className="text-sm text-slate-400">Backend: <span className="font-mono">{API_URL}</span> • Allow: {ACCEPT} • Max {MAX_MB} MB</p>

      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        className="rounded-xl border-2 border-dashed border-slate-700 bg-slate-900 p-8 text-center"
      >
        <p className="text-sm text-slate-300">Drag & drop dataset here, or</p>
        <label className="mt-3 inline-block cursor-pointer rounded bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700">
          Choose file
          <input type="file" accept={ACCEPT} className="hidden" onChange={(e) => onFile(e.target.files?.[0] || null)} />
        </label>
        {file && <p className="mt-4 font-mono text-sm">{file.name} • {(file.size / 1024).toFixed(1)} KB</p>}
      </div>

      {error && <div className="rounded border border-red-900 bg-red-950 px-4 py-3 text-sm text-red-200">{error}</div>}

      <button
        onClick={submit}
        disabled={!file || busy}
        className="w-full rounded bg-emerald-500 py-3 font-semibold text-slate-950 disabled:opacity-50 hover:bg-emerald-400"
      >
        {busy ? "Uploading & queuing… (backend may cold-start ~30s)" : "Analyze → watch live graph"}
      </button>

      <p className="text-xs text-slate-500">Files are processed privately on the HF Spaces backend and deleted when you delete the run. Nothing is kept on Netlify.</p>
    </div>
  );
}
