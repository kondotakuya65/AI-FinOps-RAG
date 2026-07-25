"""Deterministic invoice qty vs report received_qty reconciliation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.ledger.queries import invoice_lines, report_rows


@dataclass
class DiscrepancyAlert:
    severity: str
    sku: str
    invoice_id: str
    invoice_qty: float
    report_received_qty: float
    report_period: str
    vendor: str | None = None
    delta: float = 0.0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload


def _month_from_invoice_date(invoice_date: str | None) -> str | None:
    if not invoice_date:
        return None
    try:
        d = date.fromisoformat(invoice_date)
    except ValueError:
        return None
    return f"{d.year:04d}-{d.month:02d}"


def reconcile_quantities(
    db: Session,
    *,
    sku: str | None = None,
    invoice_id: str | None = None,
    vendor: str | None = None,
    only_mismatches: bool = True,
) -> list[DiscrepancyAlert]:
    """
    Pair invoice line qty with the product-report received_qty for the same SKU
    in the invoice's calendar month (when available).
    """
    inv_lines = invoice_lines(db, sku=sku, invoice_id=invoice_id, vendor=vendor)
    alerts: list[DiscrepancyAlert] = []

    for inv in inv_lines:
        period = _month_from_invoice_date(inv.get("invoice_date"))
        reports = report_rows(
            db,
            sku=inv["sku"],
            period=period,
            vendor=inv.get("vendor"),
        )
        if not reports and period:
            # fall back: any period for SKU
            reports = report_rows(db, sku=inv["sku"], vendor=inv.get("vendor"))

        if not reports:
            continue

        # Prefer exact period match; else first row
        report = next((r for r in reports if r.get("period") == period), reports[0])
        inv_qty = float(inv.get("qty") or 0)
        recv = float(report.get("received_qty") or 0)
        if only_mismatches and inv_qty == recv:
            continue
        if inv_qty == recv:
            continue

        delta = round(inv_qty - recv, 2)
        alerts.append(
            DiscrepancyAlert(
                severity="quantity_mismatch",
                sku=str(inv["sku"]),
                invoice_id=str(inv.get("invoice_id") or ""),
                invoice_qty=inv_qty,
                report_received_qty=recv,
                report_period=str(report.get("period") or period or ""),
                vendor=inv.get("vendor"),
                delta=delta,
                message=(
                    f"Discrepancy Alert: {inv.get('invoice_id')} billed {inv_qty:g} units of "
                    f"{inv['sku']}, but product report {report.get('period')} shows "
                    f"received_qty={recv:g} (short {delta:g})."
                ),
            )
        )
    return alerts


def reconcile_all_mismatches(db: Session) -> list[DiscrepancyAlert]:
    return reconcile_quantities(db, only_mismatches=True)
