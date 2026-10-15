import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";
import { ClerkProvider } from "@clerk/nextjs";
import { AuthButtons } from "@/lib/auth";

const clerkEnabled = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

function Providers({ children }: { children: ReactNode }) {
  return clerkEnabled ? <ClerkProvider telemetry={false}>{children}</ClerkProvider> : <>{children}</>;
}

export const metadata = {
  title: "DataForge AI — Autonomous BI Engineer",
  description:
    "Upload a CSV/Excel/Parquet/JSON and get executive KPIs, insights, charts and a report from 13 autonomous agents.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <Providers>
    <html lang="en">
      <body className="min-h-screen antialiased">
        <header className="sticky top-0 z-10 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
            <Link href="/" className="font-bold tracking-tight">
              DataForge <span className="text-emerald-400">AI</span> <span className="text-slate-500 text-xs ml-2">v2 • autonomous BI</span>
            </Link>
            <div className="flex items-center gap-4 text-sm">
              <Link href="/upload" className="rounded bg-emerald-500 px-3 py-1.5 font-medium text-slate-950 hover:bg-emerald-400">
                Upload dataset
              </Link>
              <Link href="/history" className="text-slate-300 hover:text-white py-1.5">
                History
              </Link>
              <a href="https://github.com/AjmalDanish/dataforge-ai" target="_blank" className="text-slate-400 hover:text-white py-1.5">
                GitHub
              </a>
              <AuthButtons />
            </div>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-4 py-10 text-center text-xs text-slate-500">
          DataForge AI v2 • Next.js + FastAPI + LangGraph • MIT licensed
        </footer>
      </body>
    </html>
    </Providers>
  );
}
