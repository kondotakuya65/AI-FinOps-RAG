"""Persist parsed documents into the SQL ledger."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document, LineItem
from app.ingest.types import ParsedDocument


def get_document_by_source(db: Session, source_file: str) -> Document | None:
    return db.scalar(select(Document).where(Document.source_file == source_file))


def replace_document_ledger(
    db: Session,
    parsed: ParsedDocument,
    content_sha256: str,
    chunk_count: int,
) -> Document:
    existing = get_document_by_source(db, parsed.source_file)
    if existing:
        db.delete(existing)
        db.flush()

    document = Document(
        source_file=parsed.source_file,
        doc_type=parsed.doc_type,
        content_sha256=content_sha256,
        vendor=parsed.vendor,
        invoice_id=parsed.invoice_id,
        currency=parsed.currency,
        total_amount=parsed.total_amount,
        period=parsed.period,
        invoice_date=parsed.invoice_date,
        payment_terms=parsed.payment_terms,
        chunk_count=chunk_count,
        extra=parsed.extra,
    )
    db.add(document)
    db.flush()

    for line in parsed.lines:
        db.add(
            LineItem(
                document_id=document.id,
                sku=line.sku,
                description=line.description,
                qty=line.qty,
                unit_price=line.unit_price,
                line_total=line.line_total,
                sold_qty=line.sold_qty,
                received_qty=line.received_qty,
                return_rate=line.return_rate,
                period=line.period or parsed.period,
                vendor=line.vendor or parsed.vendor,
                row_kind=line.row_kind,
            )
        )
    db.flush()
    return document
