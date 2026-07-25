"""Table-aware chunking: row groups with repeated column headers + metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ingest.types import ParsedDocument, ParsedLine


@dataclass
class Chunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]


def _line_as_row(line: ParsedLine, columns: list[str]) -> str:
    values: list[str] = []
    mapping = {
        "sku": line.sku,
        "description": line.description,
        "qty": line.qty,
        "unit_price": line.unit_price,
        "line_total": line.line_total,
        "sold_qty": line.sold_qty,
        "received_qty": line.received_qty,
        "return_rate": line.return_rate,
        "period": line.period,
        "vendor": line.vendor,
    }
    for col in columns:
        key = col.lower().replace(" ", "_")
        val = mapping.get(key)
        values.append("" if val is None else str(val))
    return " | ".join(values)


def _header_line(columns: list[str]) -> str:
    return " | ".join(columns)


def chunk_document(doc: ParsedDocument, row_size: int = 12) -> list[Chunk]:
    """Split tabular rows into batches; repeat headers in every chunk."""
    chunks: list[Chunk] = []
    base_meta: dict[str, Any] = {
        "source_file": doc.source_file,
        "doc_type": doc.doc_type,
        "vendor": doc.vendor or "",
        "invoice_id": doc.invoice_id or "",
        "currency": doc.currency or "",
        "period": doc.period or "",
        "invoice_date": doc.invoice_date or "",
        "payment_terms": doc.payment_terms or "",
        "total_amount": doc.total_amount if doc.total_amount is not None else "",
        "total_line_items": len(doc.lines),
    }

    # Document-level summary chunk (helps retrieval of totals / terms)
    summary_bits = [
        f"Document type: {doc.doc_type}",
        f"Source file: {doc.source_file}",
    ]
    if doc.vendor:
        summary_bits.append(f"Vendor: {doc.vendor}")
    if doc.invoice_id:
        summary_bits.append(f"Invoice ID: {doc.invoice_id}")
    if doc.invoice_date:
        summary_bits.append(f"Invoice date: {doc.invoice_date}")
    if doc.period:
        summary_bits.append(f"Period: {doc.period}")
    if doc.total_amount is not None:
        summary_bits.append(f"Total amount: {doc.total_amount} {doc.currency or ''}".strip())
    if doc.payment_terms:
        summary_bits.append(f"Payment terms: {doc.payment_terms}")
    if doc.text_body:
        summary_bits.append(doc.text_body[:1200])

    chunks.append(
        Chunk(
            chunk_id=f"{doc.source_file}::summary",
            text="\n".join(summary_bits),
            metadata={**base_meta, "chunk_kind": "summary"},
        )
    )

    if not doc.lines:
        return chunks

    columns = doc.columns or ["sku", "description", "qty", "unit_price", "line_total"]
    header = _header_line(columns)
    size = max(1, row_size)

    for start in range(0, len(doc.lines), size):
        batch = doc.lines[start : start + size]
        rows = [_line_as_row(line, columns) for line in batch]
        text = "\n".join([header, *rows])
        chunks.append(
            Chunk(
                chunk_id=f"{doc.source_file}::rows:{start}-{start + len(batch) - 1}",
                text=text,
                metadata={
                    **base_meta,
                    "chunk_kind": "table_rows",
                    "row_start": start,
                    "row_end": start + len(batch) - 1,
                },
            )
        )
    return chunks
