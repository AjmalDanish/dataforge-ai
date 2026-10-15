"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { analyzeSample } from "@/lib/api";

export default function SampleButton({ name }: { name: string }) {
  const router = useRouter();
  const [state, setState] = useState<"idle" | "busy" | "error">("idle");

  return (
    <button
      onClick={async () => {
        setState("busy");
        try {
          const run = await analyzeSample(name);
          router.push(`/runs/${run.run_id}`);
        } catch {
          setState("error");
        }
      }}
      disabled={state === "busy"}
      className="text-sm text-emerald-400 hover:text-emerald-300 disabled:opacity-60"
    >
      {state === "busy" ? "Uploading…" : state === "error" ? "API unreachable — retry" : "Analyze →"}
    </button>
  );
}
