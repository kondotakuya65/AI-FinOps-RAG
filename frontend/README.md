# Frontend — AI-FinOps-RAG

Next.js App Router workspace: corpus ingest, FinOps Q&A, discrepancy alerts.

## Brand

- Favicon / icon: `public/fav.png` (from repo root `fav.png`)
- App Router icon: `src/app/icon.png`

## Quick start

```bash
# terminal 1 — backend
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# terminal 2 — frontend
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000

`next.config.ts` rewrites `/api/*` → `API_PROXY_TARGET` (default `http://localhost:8000`).

## Demo flow

1. Click **Load fixtures**
2. Ask *“Are there quantity mismatches … SKU-1001?”* (or use a demo chip)
3. Inspect the **Discrepancy alerts** panel + answer / sources

## Docker

From repo root (with `.env` present):

```bash
docker compose up --build
```

- UI: http://localhost:3000  
- API: http://localhost:8000/docs  
