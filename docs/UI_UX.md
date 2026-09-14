# DataForge AI v2.0 — UI/UX Spec (Next.js + Tailwind, Netlify)

> Implements `docs/PRD.md` stories. Backend: HF Spaces API (`docs/TRD.md` §2). Mobile-first, dark analyst theme.

## 1. Design system
Tailwind + shadcn-style tokens: bg slate-950, cards slate-900, accent emerald-400 (KPIs) / amber-400 (risks), mono for numbers. Plotly.js charts (dynamic import, no SSR). KPI card: name, value, delta chip, sparkline, benchmark caption.

## 2. Routes (`frontend/app/`)
| Route | Purpose | Key components |
|---|---|---|
| `/` | Landing: value prop, live demo CTA, 5 sample datasets, architecture strip | Hero, SampleGallery, HowItWorks |
| `/upload` | Drag-drop + validation (ext/size/rows), domain hint select | Dropzone, FileChecks, domain_hint |
| `/runs/[id]` | Live run: SVG agent graph (13 nodes, queued/running/done/skip/error), event log, progress | GraphCanvas, EventFeed, PhaseStepper |
| `/dashboard/[id]` | KPI row + trend + distribution grid + heatmap + performers tables | KpiGrid, TrendChart, DistGrid, Heatmap |
| `/report/[id]` | Executive summary, findings, risks, recommendations, methodology, downloads | InsightCards, DownloadBar |
| `/history` | Past runs table (dataset, domain, duration, quality) + share links | RunsTable |

## 3. States (every page)
Empty (no runs yet → CTA upload) / Loading (skeleton + cold-start notice "waking backend…") / Error (upload rejected, run failed with `quality_errors` + retry) / Success. WS reconnect with backoff; fallback to 3s polling.

## 4. Graph visualization
Static 13-node layout grouped by 7 phases; node colors by status; edges highlight on completion; click node → side panel (inputs/outputs, duration, quality_score, notes). Pure SVG + CSS transitions (no lib needed for MVP).

## 5. Responsive / a11y
Single-column <768px, KPI horizontal scroll; contrast AA; keyboard-navigable upload; `aria-live` on run status; reduced-motion respected.

## 6. Netlify config
`frontend/netlify.toml`: build `npm run build`, publish `.next`, `[[redirects]] /* /index.html 200` off (App Router), env `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_WS_URL`, headers cache for `/_next/static/*`. Preview deploys per PR.
