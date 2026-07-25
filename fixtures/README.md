# Fixtures

Synthetic FinOps documents with known ground truth (for demos + eval).

| Path | Contents (upcoming) |
| --- | --- |
| `invoices/` | PDF invoices with varied table layouts |
| `reports/` | Monthly product performance `.xlsx` |
| `contracts/` | Vendor payment terms `.docx` |
| `evals/golden_qa.json` | Expected answers / discrepancy flags |

Intentional mismatches (e.g. invoice qty vs received qty) will be baked in so the reconcile engine can demo **Discrepancy Alerts**.
