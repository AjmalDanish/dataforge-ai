"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { analyzeSample } from "@/lib/api";
import { useApiToken } from "@/lib/auth";

export default function SampleButton({ name }: { name: string }) {
  const router = useRouter();
  const getToken = useApiToken();
  const [state, setState] = useState<"idle" | "busy" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  return (
    <div className="text-right">
      <button
        onClick={async () => {
          setState("busy");
          setMessage(null);
          try {
            // Signed in: the run is yours (shows in History). Signed out: a private share link.
            const run = await analyzeSample(name, getToken);
            router.push(run.run_page);
          } catch (e) {
            setState("error");
            setMessage(e instanceof Error ? e.message : String(e));
          }
        }}
        disabled={state === "busy"}
        className="text-sm text-emerald-400 hover:text-emerald-300 disabled:opacity-60"
      >
        {state === "busy" ? "Starting…" : state === "error" ? "Retry →" : "Analyze →"}
      </button>
      {message && <p className="mt-1 max-w-xs text-xs text-red-300">{message}</p>}
    </div>
  );
}
