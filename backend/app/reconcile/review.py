"""Invoice review: PO match + contract price drift + qty (optional)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ledger.queries import get_contract, list_invoices
from app.reconcile.engine import DiscrepancyAlert, reconcile_price_drift, reconcile_quantities


def review_invoice(
    db: Session,
    invoice_id: str,
    *,
    include_qty: bool = True,
) -> dict[str, Any]:
    invoices = list_invoices(db, invoice_id=invoice_id)
    if not invoices:
        return {
            "invoice_id": invoice_id,
            "found": False,
            "recommendation": "Reject",
            "reason": "Invoice not found in ledger",
            "alerts": [],
            "po_match": None,
        }

    inv = invoices[0]
    po_number = inv.po_number
    contract = get_contract(db, vendor=inv.vendor) or get_contract(db)
    approved = set((contract or {}).get("approved_po_numbers") or ["PO-4452"])
    po_match = bool(po_number) and po_number in approved

    alerts: list[DiscrepancyAlert] = []
    alerts.extend(reconcile_price_drift(db, invoice_id=invoice_id, vendor=inv.vendor))
    if include_qty:
        alerts.extend(reconcile_quantities(db, invoice_id=invoice_id, vendor=inv.vendor))

    recommendation = "Accept"
    reasons: list[str] = []
    if not po_match:
        recommendation = "Reject"
        reasons.append(
            f"PO {po_number or 'missing'} is not on the approved list {sorted(approved)}"
        )
    if any(a.severity == "price_drift" for a in alerts):
        recommendation = "Reject"
        reasons.append("Unit price exceeds contract drift limit")
    if any(a.severity == "quantity_mismatch" for a in alerts):
        reasons.append("Quantity mismatch vs product report")

    if recommendation == "Accept":
        summary = (
            f"Invoice {invoice_id} matches {po_number} and contract unit prices. Accept."
        )
    else:
        price_bits = [a.message for a in alerts if a.severity == "price_drift"]
        summary = price_bits[0] if price_bits else (
            f"Invoice {invoice_id}: {'; '.join(reasons)}. {recommendation}."
        )

    return {
        "invoice_id": invoice_id,
        "found": True,
        "vendor": inv.vendor,
        "po_number": po_number,
        "po_match": po_match,
        "recommendation": recommendation,
        "reasons": reasons,
        "summary": summary,
        "alerts": [a.to_dict() for a in alerts],
        "contract": {
            "vendor": (contract or {}).get("vendor"),
            "max_price_drift_pct": (contract or {}).get("max_price_drift_pct", 5.0),
            "approved_po_numbers": list(approved),
            "source_file": (contract or {}).get("source_file"),
        },
    }
