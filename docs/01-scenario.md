# 01 — Project scenario

## One-line pitch

An e-commerce finance team is drowning in **vendor invoices (PDF)** and **monthly product reports (Excel)**. They need an AI that answers spend questions **with exact numbers** and **flags quantity mismatches** across documents — not a chatbot that guesses totals.

## Business context

A mid-sized e-commerce company receives many vendor invoices daily plus monthly SKU-level performance reports. Accountants currently:

1. Open each PDF and re-key line items  
2. Cross-check received quantities against product reports  
3. Look up payment terms in contracts (e.g. Net-30)  

Mistakes are costly: overpaying, missing short-ships, and slow month-end close.

## What the product must do

| Capability | Example user ask | Expected behavior |
| --- | --- | --- |
| **Spend Q&A** | “How much did we spend on Vendor Alpha in Q3?” | Exact currency total from the **SQL ledger**, with cited invoices |
| **Filtered retrieval** | “Invoices over $5,000” | Metadata / SQL filter first, then semantic context |
| **Reconciliation** | “Does invoice #102 match what we received?” | Compare invoice qty vs report received qty; emit **Discrepancy Alert** if mismatch |
| **Contract context** | “What are Vendor Alpha payment terms?” | Retrieve contract clause (Net-30, etc.) via text RAG |
| **Explainability** | Any numeric answer | Markdown summary: docs used, computed figures, confidence note |

## Why this is harder than resume RAG

| Resume / narrative docs | FinOps docs |
| --- | --- |
| Paragraphs and bullets | Tables, line items, currencies |
| One document at a time | Joint retrieval across **invoice + report (+ contract)** |
| Soft scoring OK | Wrong `$` or qty is a product failure |
| Chunk by characters | Chunk by **row groups** with **repeated headers** |

If you split a table in half without headers, the model loses column meaning and the math breaks.

## Demo story (portfolio walkthrough)

1. Open the Next.js UI (brand favicon from `fav.png`).  
2. Corpus already ingested: sample invoices, 2–3 monthly reports, one vendor contract.  
3. Ask: *“How much did we spend on Vendor Alpha in Q3?”* → see a computed total + source table.  
4. Ask: *“Any quantity mismatches for SKU-1001?”* → **Discrepancy Alert** (invoice says 500, report says 450).  
5. Toggle `LLM_PROVIDER` between Ollama `phi3:mini` and OpenAI — same API, different explainer.

## Out of scope for MVP

- Live ERP / QuickBooks connectors  
- Full OCR of scanned photos (synthetic vector PDFs first)  
- Autonomous payment approval  
- Multi-tenant SaaS billing  

Stretch (later): upload a new invoice → “matches PO #4452, but unit price is 5% over contract — reject.”

## Success criteria

- Recruiter can clone, set `.env`, run backend (+ optional Ollama), and hit a working health/query path.  
- At least one **intentional discrepancy** in fixtures is detected **without** the LLM doing arithmetic.  
- README + these docs make the RAG-vs-ledger design obvious in under five minutes.
