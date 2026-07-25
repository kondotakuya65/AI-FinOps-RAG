"""Shared parsed-document shapes for ingest."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ParsedLine:
    sku: Optional[str] = None
    description: Optional[str] = None
    qty: Optional[float] = None
    unit_price: Optional[float] = None
    line_total: Optional[float] = None
    sold_qty: Optional[float] = None
    received_qty: Optional[float] = None
    return_rate: Optional[float] = None
    period: Optional[str] = None
    vendor: Optional[str] = None
    row_kind: str = "line"
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    source_file: str
    doc_type: str  # invoice | report | contract
    vendor: Optional[str] = None
    invoice_id: Optional[str] = None
    currency: Optional[str] = None
    total_amount: Optional[float] = None
    period: Optional[str] = None
    invoice_date: Optional[str] = None
    payment_terms: Optional[str] = None
    columns: list[str] = field(default_factory=list)
    lines: list[ParsedLine] = field(default_factory=list)
    text_body: str = ""
    extra: dict[str, Any] = field(default_factory=dict)
