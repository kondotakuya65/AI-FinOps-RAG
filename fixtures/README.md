# Fixtures

Synthetic FinOps documents generated from a single ground-truth source.

| Path | Contents |
| --- | --- |
| `ground_truth.json` | Authoritative vendors, invoices, reports, discrepancies, aggregates |
| `invoices/` | 8 PDF invoices (layouts: table top/middle/bottom; column order variants) |
| `reports/` | 3 monthly product performance `.xlsx` (2024-07 … 2024-09) |
| `contracts/` | Alpha Supplies agreement (Net-30 + unit prices) |
| `evals/golden_qa.json` | Demo / eval questions aligned with ground truth |

## Regenerate

```bash
# from repo root (backend venv with reportlab/openpyxl/python-docx)
cd backend
.\.venv\Scripts\python ..\scripts\generate_fixtures.py
# or: make fixtures
```

Do not hand-edit generated PDFs/XLSX/DOCX — change `scripts/generate_fixtures.py` and regenerate so math stays consistent.

## Demo highlights

- **Alpha Supplies 2024-Q3 spend:** `$10,675.22` (INV-101 + INV-102 + INV-103)
- **Discrepancy:** INV-102 SKU-1001 qty **500** vs Aug report received **450**
- Also short: INV-201 (200 vs 180), INV-301 (100 vs 95)
