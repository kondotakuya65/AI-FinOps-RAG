# 02 — Architecture

## High-level

```text
Next.js UI
    │  upload / ask / view alerts
    ▼
FastAPI
    ├─ Ingest  → parse tables → header-aware chunks → embed → Chroma
    │              └──────── → line items / totals → SQL ledger
    ├─ Retrieve → hybrid (Chroma + BM25 + SQL filters)
    ├─ Reconcile → deterministic qty/amount compare
    └─ LLM adapter (ollama | openai) → explain + markdown dashboard
```

**Hard rule:** RAG finds *which* rows/docs matter; **SQL/Pandas compute** money and quantities; the LLM **narrates** and highlights alerts.

## Components

### Frontend (`frontend/`)

- Next.js App Router + TypeScript  
- Brand asset: `public/fav.png` (also `src/app/icon.png` for the tab favicon)  
- Screens (planned): upload, query console, discrepancy panel, recent queries  

### Backend (`backend/app/`)

| Package | Responsibility |
| --- | --- |
| `api/` | REST: health, ingest, query, history |
| `db/` | SQLAlchemy models + session (`sqlite` \| `postgres`) |
| `ingest/` | PDF / XLSX / DOCX parsers + table-aware chunking |
| `ledger/` | Authoritative line items and document totals |
| `retrieve/` | Chroma vectors, BM25, hybrid merge |
| `reconcile/` | Invoice ↔ report mismatch detection |
| `llm/` | Provider switch (Ollama / OpenAI) |

### Stores

| Store | Holds | Why separate |
| --- | --- | --- |
| **App DB** (SQLite/Postgres) | Document registry, query history, **ledger rows** | Exact filters & joins |
| **Chroma** | Text chunks + embeddings + chunk metadata | Semantic search |
| **Disk** | Uploads + persist dir for Chroma | Content-hash cache skips re-embed |

## Ingest pipeline

1. Accept file (or load from `fixtures/`).  
2. Detect type → extract tables as structured lines (pdfplumber / pandas / python-docx).  
3. **Chunk by row groups** (default 12 rows), **repeat headers** in every chunk + a summary chunk.  
4. Attach metadata: `source_file`, `doc_type`, `vendor`, `invoice_id`, `currency`, `total_amount`, `period`, …  
5. Upsert ledger rows (SKU, qty, unit_price, amount, dates).  
6. Embed chunks → Chroma; **skip if `content_sha256` unchanged** (`POST /api/ingest`, `python -m app.ingest.cli`).

## Query pipeline

1. Parse intent with lightweight rules (spend / filter / reconcile / contract).  
2. Apply **SQL ledger** filters/aggregates when the question implies numbers or IDs.  
3. **Hybrid retrieve**: BM25 (IDs/SKUs) + Chroma vectors, merged with reciprocal rank fusion.  
4. For reconcile intents: compare invoice qty vs report `received_qty` in code → **Discrepancy Alert**.  
5. Build a structured facts pack (numbers already computed).  
6. LLM (ollama | openai | mock) explains without changing totals; response includes markdown dashboard.

API: `POST /api/query` `{ "question": "...", "use_llm": true }`.

## Config surface (env)

See root `.env.example`:

- `LLM_PROVIDER=ollama|openai` + model URLs/keys  
- `DATABASE_URL` sqlite or postgres  
- `EMBEDDING_PROVIDER=local|openai`  
- `CHROMA_PERSIST_DIR`, `UPLOAD_DIR`  

Same “switch the provider with env” philosophy as the Code Reviewer and Resume Reviewer samples.

## Security / demo notes

- No secrets in git (`.env` ignored).  
- Synthetic fixtures only in public demos.  
- LLM output labeled as assistive — accountants remain decision makers.
