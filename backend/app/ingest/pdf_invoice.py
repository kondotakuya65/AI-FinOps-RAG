"""Parse invoice PDFs into structured line items via pdfplumber."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

import pdfplumber

from app.ingest.types import ParsedDocument, ParsedLine

_MONEY_RE = re.compile(r"[,$]")


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "-"}:
        return None
    text = _MONEY_RE.sub("", text)
    try:
        return float(text)
    except ValueError:
        return None


def _norm_header(cell: Any) -> str:
    text = str(cell or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    aliases = {
        "sku": "sku",
        "description": "description",
        "desc": "description",
        "qty": "qty",
        "quantity": "qty",
        "unit price": "unit_price",
        "unit_price": "unit_price",
        "price": "unit_price",
        "line total": "line_total",
        "line_total": "line_total",
        "total": "line_total",
        "amount": "line_total",
    }
    return aliases.get(text, text.replace(" ", "_"))


def _extract_meta(text: str) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    inv = re.search(r"INVOICE\s+(INV-\d+)", text, re.I)
    if inv:
        meta["invoice_id"] = inv.group(1).upper()
    vendor = re.search(r"Vendor:\s*(.+)", text, re.I)
    if vendor:
        meta["vendor"] = vendor.group(1).strip().split("\n")[0].strip()
    date = re.search(r"Date:\s*(\d{4}-\d{2}-\d{2})", text, re.I)
    if date:
        meta["invoice_date"] = date.group(1)
    currency = re.search(r"Currency:\s*([A-Z]{3})", text, re.I)
    if currency:
        meta["currency"] = currency.group(1).upper()
    total = re.search(r"Invoice Total:\s*\$?\s*([\d,]+\.\d{2})", text, re.I)
    if total:
        meta["total_amount"] = _to_float(total.group(1))
    return meta


def _rows_from_table(table: list[list[Any]]) -> tuple[list[str], list[ParsedLine]]:
    if not table or len(table) < 2:
        return [], []
    headers = [_norm_header(c) for c in table[0]]
    lines: list[ParsedLine] = []
    for raw in table[1:]:
        if not raw or all(cell is None or str(cell).strip() == "" for cell in raw):
            continue
        mapped = {
            headers[i]: (raw[i] if i < len(raw) else None)
            for i in range(len(headers))
        }
        sku = str(mapped.get("sku") or "").strip() or None
        if not sku:
            continue
        qty = _to_float(mapped.get("qty"))
        unit_price = _to_float(mapped.get("unit_price"))
        line_total = _to_float(mapped.get("line_total"))
        if line_total is None and qty is not None and unit_price is not None:
            line_total = round(qty * unit_price, 2)
        lines.append(
            ParsedLine(
                sku=sku,
                description=str(mapped.get("description") or "").strip() or None,
                qty=qty,
                unit_price=unit_price,
                line_total=line_total,
                row_kind="line",
            )
        )
    return headers, lines


def parse_invoice_pdf(path: Path) -> ParsedDocument:
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[0]
        text = page.extract_text() or ""
        tables = page.extract_tables() or []

    meta = _extract_meta(text)
    columns: list[str] = []
    lines: list[ParsedLine] = []
    for table in tables:
        cols, parsed = _rows_from_table(table)
        if parsed:
            columns = cols
            lines = parsed
            break

    if meta.get("total_amount") is None and lines:
        meta["total_amount"] = round(
            sum(line.line_total or 0.0 for line in lines),
            2,
        )

    return ParsedDocument(
        source_file=path.name,
        doc_type="invoice",
        vendor=meta.get("vendor"),
        invoice_id=meta.get("invoice_id"),
        currency=meta.get("currency", "USD"),
        total_amount=meta.get("total_amount"),
        invoice_date=meta.get("invoice_date"),
        columns=columns or ["sku", "description", "qty", "unit_price", "line_total"],
        lines=lines,
        text_body=text,
        extra={"parser": "pdfplumber"},
    )
