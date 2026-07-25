"""SQL ledger queries — authoritative numbers for filters and aggregates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Document, LineItem

_QUARTER_BOUNDS = {
    1: ("01-01", "03-31"),
    2: ("04-01", "06-30"),
    3: ("07-01", "09-30"),
    4: ("10-01", "12-31"),
}


@dataclass
class InvoiceRecord:
    invoice_id: str
    vendor: str
    invoice_date: str | None
    total_amount: float
    currency: str
    source_file: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def quarter_date_range(period: str) -> tuple[str, str]:
    """Parse '2024-Q3' or 'Q3 2024' → (start, end) ISO dates."""
    text = period.strip().upper().replace(" ", "")
    year = None
    q = None
    if "-Q" in text:
        year_s, q_s = text.split("-Q", 1)
        year, q = int(year_s), int(q_s)
    elif text.startswith("Q") and len(text) >= 2:
        q = int(text[1])
        year = date.today().year
    else:
        raise ValueError(f"Unsupported period: {period}")
    start_md, end_md = _QUARTER_BOUNDS[q]
    return f"{year}-{start_md}", f"{year}-{end_md}"


def list_invoices(
    db: Session,
    *,
    vendor: str | None = None,
    min_total: float | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    invoice_id: str | None = None,
) -> list[InvoiceRecord]:
    stmt = select(Document).where(Document.doc_type == "invoice")
    if vendor:
        stmt = stmt.where(Document.vendor.ilike(f"%{vendor}%"))
    if min_total is not None:
        stmt = stmt.where(Document.total_amount > min_total)
    if date_from:
        stmt = stmt.where(Document.invoice_date >= date_from)
    if date_to:
        stmt = stmt.where(Document.invoice_date <= date_to)
    if invoice_id:
        stmt = stmt.where(Document.invoice_id == invoice_id)
    stmt = stmt.order_by(Document.invoice_date.asc())
    rows = db.scalars(stmt).all()
    return [
        InvoiceRecord(
            invoice_id=r.invoice_id or "",
            vendor=r.vendor or "",
            invoice_date=r.invoice_date,
            total_amount=float(r.total_amount or 0.0),
            currency=r.currency or "USD",
            source_file=r.source_file,
        )
        for r in rows
    ]


def sum_invoice_spend(
    db: Session,
    *,
    vendor: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    invoices = list_invoices(
        db,
        vendor=vendor,
        date_from=date_from,
        date_to=date_to,
    )
    total = round(sum(i.total_amount for i in invoices), 2)
    return {
        "vendor": vendor,
        "date_from": date_from,
        "date_to": date_to,
        "total_amount": total,
        "currency": invoices[0].currency if invoices else "USD",
        "invoice_count": len(invoices),
        "invoices": [i.to_dict() for i in invoices],
    }


def get_contract(db: Session, vendor: str | None = None) -> dict[str, Any] | None:
    stmt = select(Document).where(Document.doc_type == "contract")
    if vendor:
        stmt = stmt.where(Document.vendor.ilike(f"%{vendor}%"))
    doc = db.scalars(stmt).first()
    if not doc:
        return None
    prices = db.scalars(select(LineItem).where(LineItem.document_id == doc.id)).all()
    return {
        "vendor": doc.vendor,
        "payment_terms": doc.payment_terms,
        "source_file": doc.source_file,
        "prices": [
            {"sku": p.sku, "unit_price": p.unit_price}
            for p in prices
            if p.row_kind == "contract_price"
        ],
    }


def invoice_lines(
    db: Session,
    *,
    sku: str | None = None,
    invoice_id: str | None = None,
    vendor: str | None = None,
) -> list[dict[str, Any]]:
    stmt = (
        select(LineItem, Document)
        .join(Document, LineItem.document_id == Document.id)
        .where(LineItem.row_kind == "line", Document.doc_type == "invoice")
    )
    if sku:
        stmt = stmt.where(LineItem.sku == sku)
    if invoice_id:
        stmt = stmt.where(Document.invoice_id == invoice_id)
    if vendor:
        stmt = stmt.where(Document.vendor.ilike(f"%{vendor}%"))
    out: list[dict[str, Any]] = []
    for line, doc in db.execute(stmt).all():
        out.append(
            {
                "sku": line.sku,
                "description": line.description,
                "qty": line.qty,
                "unit_price": line.unit_price,
                "line_total": line.line_total,
                "invoice_id": doc.invoice_id,
                "vendor": doc.vendor,
                "invoice_date": doc.invoice_date,
                "source_file": doc.source_file,
            }
        )
    return out


def report_rows(
    db: Session,
    *,
    sku: str | None = None,
    period: str | None = None,
    vendor: str | None = None,
) -> list[dict[str, Any]]:
    stmt = (
        select(LineItem, Document)
        .join(Document, LineItem.document_id == Document.id)
        .where(LineItem.row_kind == "report", Document.doc_type == "report")
    )
    if sku:
        stmt = stmt.where(LineItem.sku == sku)
    if period:
        stmt = stmt.where(or_(LineItem.period == period, Document.period == period))
    if vendor:
        stmt = stmt.where(
            or_(LineItem.vendor.ilike(f"%{vendor}%"), Document.vendor.ilike(f"%{vendor}%"))
        )
    out: list[dict[str, Any]] = []
    for line, doc in db.execute(stmt).all():
        out.append(
            {
                "sku": line.sku,
                "vendor": line.vendor or doc.vendor,
                "sold_qty": line.sold_qty,
                "received_qty": line.received_qty,
                "return_rate": line.return_rate,
                "period": line.period or doc.period,
                "source_file": doc.source_file,
            }
        )
    return out
