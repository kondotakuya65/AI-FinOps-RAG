"""Lightweight rule-based intent parsing for FinOps questions."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

IntentType = Literal[
    "spend_aggregate",
    "invoice_filter",
    "reconcile",
    "price_review",
    "contract_terms",
    "general",
]

_VENDOR_ALIASES = {
    "alpha": "Alpha Supplies",
    "alpha supplies": "Alpha Supplies",
    "vendor alpha": "Alpha Supplies",
    "beta": "Beta Parts",
    "beta parts": "Beta Parts",
    "gamma": "Gamma Logistics",
    "gamma logistics": "Gamma Logistics",
}


@dataclass
class QueryIntent:
    intent: IntentType
    vendor: str | None = None
    sku: str | None = None
    invoice_id: str | None = None
    period: str | None = None  # e.g. 2024-Q3
    min_total: float | None = None
    raw_question: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _extract_vendor(text: str) -> str | None:
    lower = text.lower()
    for alias, canonical in sorted(_VENDOR_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if alias in lower:
            return canonical
    return None


def _extract_period(text: str) -> str | None:
    m = re.search(r"(20\d{2})\s*[- ]\s*Q([1-4])", text, re.I)
    if m:
        return f"{m.group(1)}-Q{m.group(2)}"
    m = re.search(r"Q([1-4])\s*(20\d{2})", text, re.I)
    if m:
        return f"{m.group(2)}-Q{m.group(1)}"
    m = re.search(r"\bQ([1-4])\b", text, re.I)
    if m:
        # demo corpus is 2024
        return f"2024-Q{m.group(1)}"
    return None


def _extract_min_total(text: str) -> float | None:
    patterns = [
        r"(?:over|above|greater than|>)\s*\$?\s*([\d,]+(?:\.\d+)?)",
        r"\$\s*([\d,]+(?:\.\d+)?)\s*(?:\+|or more)?",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m and ("over" in text.lower() or "above" in text.lower() or ">" in text or "+" in text):
            return float(m.group(1).replace(",", ""))
    m = re.search(r"over\s*\$?\s*([\d,]+)", text, re.I)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def parse_intent(question: str) -> QueryIntent:
    q = question.strip()
    lower = q.lower()
    vendor = _extract_vendor(q)
    sku_m = re.search(r"SKU-\d+", q, re.I)
    sku = sku_m.group(0).upper() if sku_m else None
    inv_m = re.search(r"INV-\d+", q, re.I)
    invoice_id = inv_m.group(0).upper() if inv_m else None
    period = _extract_period(q)
    min_total = _extract_min_total(q)

    intent: IntentType = "general"
    notes: list[str] = []

    if any(
        w in lower
        for w in (
            "accept",
            "reject",
            "price drift",
            "unit price",
            "over contract",
            "against the",
            "po-",
            "purchase order",
        )
    ) and (
        inv_m
        or "contract" in lower
        or "po-" in lower
        or "price" in lower
    ):
        intent = "price_review"
    elif any(
        w in lower
        for w in (
            "mismatch",
            "discrepan",
            "received everything",
            "short-ship",
            "quantity",
            "qty",
        )
    ) or ("receive" in lower and ("bill" in lower or "invoice" in lower)):
        intent = "reconcile"
    elif any(w in lower for w in ("payment term", "net-", "contract")):
        intent = "contract_terms"
    elif min_total is not None or (
        "invoice" in lower and any(w in lower for w in ("over", "above", "greater"))
    ):
        intent = "invoice_filter"
        if min_total is None:
            min_total = _extract_min_total(q) or 5000.0
            notes.append("defaulted min_total heuristic")
    elif any(w in lower for w in ("how much", "spend", "spent", "total cost", "paid")):
        intent = "spend_aggregate"

    return QueryIntent(
        intent=intent,
        vendor=vendor,
        sku=sku,
        invoice_id=invoice_id,
        period=period,
        min_total=min_total,
        raw_question=q,
        notes=notes,
    )
