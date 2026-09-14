import "./globals.css";
import Link from "next/link";

export const metadata = {
  title: "DataForge AI — Autonomous BI Engineer",
  description:
    "Upload a CSV/Excel/Parquet/JSON and get executive KPIs, insights, dashboard and report. Built for Data Scientist / ML roles.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <header className="sticky top-0 z-10 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
            <Link href="/" className="font-bold tracking-tight">
              DataForge <span className="text-emerald-400">AI</span> <span className="text-slate-500 text-xs ml-2">v2 • autonomous BI</span>
            </Link>
            <div className="flex gap-4 text-sm">
              <Link href="/upload" className="rounded bg-emerald-500 px-3 py-1.5 font-medium text-slate-950 hover:bg-emerald-400">
                Upload dataset
              </Link>
              <Link href="/history" className="text-slate-300 hover:text-white py-1.5">
                History
              </Link>
              <a href="https://github.com/AjmalDanish/dataforge-ai" target="_blank" className="text-slate-400 hover:text-white py-1.5">
                GitHub
              </a>
            </div>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-4 py-10 text-center text-xs text-slate-500">
          Built for Data Scientist / ML roles • Next.js on Netlify + FastAPI on HF Spaces + Neon Postgres • See docs/PRD.md → TRD.md → UI_UX.md → DATABASE.md
        </footer>
      </body>
    </html>
  );
}
