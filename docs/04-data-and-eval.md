# 04 — Data & evaluation

## Fixture layout

```text
fixtures/
├── invoices/          # 8 PDF invoices (varied layouts)
├── reports/           # 3 monthly product performance .xlsx
├── contracts/         # vendor terms .docx
├── ground_truth.json  # authoritative totals & mismatches
└── evals/
    └── golden_qa.json # question → expected behavior
```

Regenerate anytime with `python scripts/generate_fixtures.py` (see `fixtures/README.md`).

## Document types

### Invoices (PDF)

Minimum fields per doc:

- `invoice_id`, `vendor`, `invoice_date`, `currency`  
- Line items: `sku`, `description`, `qty`, `unit_price`, `line_total`  
- `total_amount`  

Layout variants to stress table extraction:

- Table in middle of page vs near footer  
- Different column orders (qty before/after price)  

### Product reports (Excel)

- Period (month / quarter)  
- Per SKU: `sold_qty`, `received_qty`, `return_rate`, optional `vendor`  

### Contract (DOCX)

- Vendor name  
- Payment terms (e.g. Net-30)  
- Optional agreed unit prices for stretch “price drift” alerts  

## Ground truth

Source of truth is coded in `scripts/generate_fixtures.py`, which writes `fixtures/ground_truth.json` and all binary docs.

Key demo aggregate:

- `aggregates.alpha_supplies_2024_q3_spend` = **10675.22** (INV-101 + INV-102 + INV-103)

Example discrepancy:

```json
{
  "id": "disc-sku-1001",
  "sku": "SKU-1001",
  "invoice_id": "INV-102",
  "invoice_qty": 500,
  "report_period": "2024-08",
  "report_received_qty": 450,
  "severity": "quantity_mismatch"
}
```

Generators write PDFs/XLSX **from** this truth so eval never depends on brittle OCR guesses.

## Golden Q&A

Starter file: `fixtures/evals/golden_qa.json`.

Eval types:

| `expect.type` | Pass condition |
| --- | --- |
| `numeric` | Answer (or structured field) within tolerance of `expected_amount` |
| `discrepancy_alert` | Response includes alert; quantities match ground truth |
| `citation` | Listed `source_file` / `invoice_id` intersects expected set |

Run evals with LLM **mocked** for CI; optional live LLM smoke job locally.

## Caching note

Ingest records `content_sha256` per file. Unchanged bytes → skip embedding. Changing a single fixture line should invalidate only that file’s vectors and ledger rows.
