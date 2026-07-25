# 05 — Design decisions

## Keep parity with sibling portfolio repos

| Decision | Rationale |
| --- | --- |
| Next.js + FastAPI | Same full-stack shape as Code Reviewer & Resume Reviewer |
| `LLM_PROVIDER=ollama\|openai\|anthropic\|mock` | One adapter; local `phi3:mini` demos without spend |
| `DATABASE_URL` sqlite \| postgres | Fast laptop demo vs Docker “real” DB |
| docker-compose | Optional one-command path for recruiters |

## Structured ledger + RAG (not pure vector RAG)

Embeddings are weak at exact amounts (`$5,430.22`) and brittle for “invoices over $5,000”.

- **Ledger (SQL):** filters, aggregates, reconcile  
- **Vectors:** semantic / contractual language  
- **BM25:** invoice IDs, SKUs, exact tokens  

Interview talking point: “We don’t ask the LLM to be a calculator.”

## Open parsers first

MVP uses **pdfplumber + pandas + openpyxl + python-docx** so clone-and-run stays free.

Deferred: LlamaParse / Unstructured as optional flags for ugly real-world PDFs.

## Chroma over Pinecone (MVP)

Local persist, no cloud API key for vectors. Stretch: Pinecone or pgvector if we want a production-shaped footnote.

## Local embeddings by default

`sentence-transformers` works offline next to Ollama. Optional OpenAI embeddings via `EMBEDDING_PROVIDER`.

## LangChain: light or none

Prefer plain Python modules for clarity in a sample repo. Add LangChain utilities only if they remove real boilerplate (e.g. later ParentDocumentRetriever).

## LLM role

Allowed: explanations, markdown dashboards, soft confidence language.  
Forbidden as source of truth: sums, qty compares, currency conversion.

## Favicon / brand

Root `fav.png` is copied into the frontend (`public/fav.png` + App Router `icon.png`) so the browser tab matches the project brand from day one of the UI.

## Explicitly deferred

- Multi-tenant auth  
- Real PO system integration  
- Heavy agent frameworks  
- Streaming token UI (nice-to-have after core query path)
