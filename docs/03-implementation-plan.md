# 03 — Implementation plan

Phased delivery so each step is demable and reviewable. Checkboxes are the working backlog.

## Phase 0 — Scaffold ✅

- [x] README, license, `.env.example`, docker-compose (API + Postgres)  
- [x] FastAPI health + settings + LLM adapter stub  
- [x] Package layout: ingest / retrieve / ledger / reconcile  
- [x] Project docs under `/docs`  
- [x] Next.js shell + brand favicon (`fav.png`)  

**Accept:** `GET /api/health` returns provider + DB scheme; UI loads at `:3000` with favicon.

## Phase 1 — Synthetic corpus ✅

- [x] Generator scripts for 5–8 invoice PDFs (varied table position)  
- [x] 2–3 monthly product report `.xlsx` files  
- [x] 1 vendor contract `.docx` (Net-30, price terms)  
- [x] `fixtures/ground_truth.json` with known totals and **2–3 intentional mismatches**  

**Accept:** Opening fixtures shows readable tables; ground truth matches spreadsheet math (`pytest` + `scripts/generate_fixtures.py`).

## Phase 2 — Ingest + ledger + index ✅

- [x] `pdfplumber` invoice tables → DataFrame/structured lines  
- [x] Excel/DOCX parsers  
- [x] Header-aware row-group chunking + metadata  
- [x] SQLAlchemy models: Document, LineItem, QueryRun  
- [x] Chroma upsert + **content-hash cache**  
- [x] CLI (`python -m app.ingest.cli`) + `POST /api/ingest`  

**Accept:** Re-running ingest skips unchanged files; ledger row counts match ground truth.

## Phase 3 — Hybrid query + reconcile ✅

- [x] BM25 index over chunk text / IDs  
- [x] SQL filters (`total_amount > N`, vendor, date range)  
- [x] Hybrid retriever merge (RRF: vector + BM25)  
- [x] Reconcile engine: invoice qty vs report received qty  
- [x] `POST /api/query` → answer, sources, alerts, markdown block  
- [x] LLM explain path via ollama / openai / mock  

**Accept:** Golden case `qty_discrepancy` returns Discrepancy Alert with correct numbers even if LLM is mocked.

## Phase 4 — Next.js UI ✅

- [x] App shell with brand favicon  
- [x] Upload + corpus status  
- [x] Query box + answer / alert panel  
- [x] Proxy `/api` → FastAPI  
- [x] Wire into docker-compose  

**Accept:** Full demo story from [01-scenario](./01-scenario.md) without using Swagger.

## Phase 5 — Eval + polish ✅

- [x] Expand `fixtures/evals/golden_qa.json`  
- [x] `pytest` eval runner (numeric tolerance + alert presence)  
- [x] README demo / screenshots section  
- [x] Optional: Anthropic provider for parity with Resume Reviewer  
- [x] GitHub Actions CI (backend golden eval + frontend build)  

**Accept:** CI runs unit tests + offline eval with mocked LLM.

## Phase 6 — Stretch

- [ ] Upload invoice → match PO / contract unit price drift  
- [ ] pgvector instead of (or beside) Chroma  
- [ ] LlamaParse behind a feature flag for messy real PDFs  

## Suggested build order (day-to-day)

1. Ground truth JSON design  
2. Excel report path (easiest DataFrame) → ledger  
3. Invoice PDF path → ledger + chunks  
4. Query spend aggregate (SQL only)  
5. Add vectors + BM25  
6. Reconcile + LLM narrative  
7. UI  

## Definition of done (portfolio)

- Clear differentiation from resume/code samples in README  
- One-command or short README path to run  
- At least one screenshot of discrepancy UI  
- Docs in `/docs` stay accurate when APIs land (update as you go)
