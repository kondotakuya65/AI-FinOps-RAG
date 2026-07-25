# Frontend — AI-FinOps-RAG

Next.js App Router UI for FinOps query, upload, and discrepancy views.

## Brand

- Favicon / icon: `public/fav.png` (sourced from repo root `fav.png`)
- App Router icon: `src/app/icon.png` (same asset)

## Quick start

```bash
cp ../.env.example ../.env   # optional; API proxy defaults to :8000
npm install
npm run dev
```

Open http://localhost:3000

`next.config.ts` rewrites `/api/*` → `API_PROXY_TARGET` (default `http://localhost:8000`).

## Planned screens

1. Corpus status + upload  
2. Query console  
3. Answer + markdown summary + **Discrepancy Alert** panel  

See [docs/03-implementation-plan.md](../docs/03-implementation-plan.md) Phase 4.
