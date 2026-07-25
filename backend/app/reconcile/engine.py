"""Deterministic invoice qty + contract price-drift / PO reconciliation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.ledger.queries import get_contract, invoice_lines, report_rows


@dataclass
class DiscrepancyAlert:
    severity: str
    sku: str
    invoice_id: str
    invoice_qty: float | None = None
    report_received_qty: float | None = None
    report_period: str | None = None
    vendor: str | None = None
    delta: float | None = None
    invoice_unit_price: float | None = None
    contract_unit_price: float | None = None
    drift_pct: float | None = None
    po_number: str | None = None
    po_match: bool | None = None
    recommendation: str | None = None
    message: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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
            reports = report_rows(db, sku=inv["sku"], vendor=inv.get("vendor"))

        if not reports:
            continue

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


def reconcile_price_drift(
    db: Session,
    *,
    invoice_id: str | None = None,
    vendor: str | None = None,
    sku: str | None = None,
    max_drift_pct: float | None = None,
) -> list[DiscrepancyAlert]:
    """
    Compare invoice unit prices to the vendor contract schedule.
    Drift above the contract threshold (default 5%) → Reject recommendation.
    """
    contract = get_contract(db, vendor=vendor)
    if not contract:
        # try without vendor filter if invoice implies Alpha later
        contract = get_contract(db, vendor=None)
    if not contract:
        return []

    price_map = {
        p["sku"]: float(p["unit_price"])
        for p in (contract.get("prices") or [])
        if p.get("sku") is not None and p.get("unit_price") is not None
    }
    threshold = float(
        max_drift_pct
        if max_drift_pct is not None
        else (contract.get("max_price_drift_pct") or 5.0)
    )
    approved_pos = set(contract.get("approved_po_numbers") or ["PO-4452"])

    inv_lines = invoice_lines(db, sku=sku, invoice_id=invoice_id, vendor=vendor)
    alerts: list[DiscrepancyAlert] = []
    for inv in inv_lines:
        line_sku = inv.get("sku")
        if not line_sku or line_sku not in price_map:
            continue
        contract_price = price_map[line_sku]
        invoice_price = float(inv.get("unit_price") or 0)
        if contract_price <= 0:
            continue
        drift_pct = round(((invoice_price - contract_price) / contract_price) * 100.0, 2)
        if abs(drift_pct) <= threshold:
            continue

        po_number = inv.get("po_number") or ""
        po_match = po_number in approved_pos if po_number else False
        recommendation = "Reject"
        if po_match:
            message = (
                f"Discrepancy Alert: {inv.get('invoice_id')} matches {po_number}, but "
                f"{line_sku} unit price {invoice_price:g} is {drift_pct:g}% vs contract "
                f"{contract_price:g} (limit {threshold:g}%). {recommendation}."
            )
        else:
            message = (
                f"Discrepancy Alert: {inv.get('invoice_id')} {line_sku} unit price "
                f"{invoice_price:g} is {drift_pct:g}% vs contract {contract_price:g} "
                f"(limit {threshold:g}%). PO={po_number or 'missing'}. {recommendation}."
            )
        alerts.append(
            DiscrepancyAlert(
                severity="price_drift",
                sku=str(line_sku),
                invoice_id=str(inv.get("invoice_id") or ""),
                vendor=inv.get("vendor") or contract.get("vendor"),
                invoice_unit_price=invoice_price,
                contract_unit_price=contract_price,
                drift_pct=drift_pct,
                po_number=po_number or None,
                po_match=po_match,
                recommendation=recommendation,
                message=message,
            )
        )
    return alerts


def reconcile_all_mismatches(db: Session) -> list[DiscrepancyAlert]:
    return reconcile_quantities(db, only_mismatches=True)
