"""Markdown dashboard renderer for query responses."""

from __future__ import annotations

from typing import Any


def render_markdown_dashboard(payload: dict[str, Any]) -> str:
    intent = payload.get("intent", {})
    facts = payload.get("facts", {})
    alerts = payload.get("alerts", [])
    sources = payload.get("sources", [])
    confidence = payload.get("confidence", {})

    lines = [
        "## FinOps query result",
        "",
        f"**Question:** {payload.get('question', '')}",
        f"**Intent:** `{intent.get('intent', 'general')}`",
        "",
        "### Answer",
        payload.get("answer", ""),
        "",
    ]

    if payload.get("explanation"):
        lines.extend(["### Explanation", "", payload["explanation"], ""])

    if alerts:
        lines.extend(["### Discrepancy alerts", ""])
        lines.append("| SKU | Invoice | Billed qty | Received qty | Period |")
        lines.append("| --- | --- | ---: | ---: | --- |")
        for alert in alerts:
            lines.append(
                f"| {alert.get('sku')} | {alert.get('invoice_id')} | "
                f"{alert.get('invoice_qty')} | {alert.get('report_received_qty')} | "
                f"{alert.get('report_period')} |"
            )
        lines.append("")

    if facts.get("spend"):
        spend = facts["spend"]
        lines.extend(
            [
                "### Spend summary",
                "",
                f"- Vendor: {spend.get('vendor')}",
                f"- Window: {spend.get('date_from')} → {spend.get('date_to')}",
                f"- **Total: {spend.get('total_amount')} {spend.get('currency')}**",
                f"- Invoices: {spend.get('invoice_count')}",
                "",
            ]
        )

    if facts.get("invoices"):
        lines.extend(
            [
                "### Matching invoices",
                "",
                "| Invoice | Vendor | Date | Total |",
                "| --- | --- | --- | ---: |",
            ]
        )
        for inv in facts["invoices"]:
            lines.append(
                f"| {inv.get('invoice_id')} | {inv.get('vendor')} | "
                f"{inv.get('invoice_date')} | {inv.get('total_amount')} |"
            )
        lines.append("")

    if facts.get("contract"):
        c = facts["contract"]
        lines.extend(
            [
                "### Contract",
                "",
                f"- Vendor: {c.get('vendor')}",
                f"- Payment terms: **{c.get('payment_terms')}**",
                f"- Source: `{c.get('source_file')}`",
                "",
            ]
        )

    if sources:
        lines.extend(
            [
                "### Retrieved documents",
                "",
                "| Source | Type | Channels |",
                "| --- | --- | --- |",
            ]
        )
        seen: set[str] = set()
        for src in sources:
            meta = src.get("metadata") or {}
            key = meta.get("source_file") or src.get("chunk_id")
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                f"| `{meta.get('source_file', key)}` | {meta.get('doc_type', '')} | "
                f"{', '.join(src.get('channels') or [])} |"
            )
        lines.append("")

    lines.extend(
        [
            "### Confidence",
            "",
            f"- Numeric source: **{confidence.get('numeric_source', 'sql_ledger')}**",
            f"- LLM role: {confidence.get('llm_role', 'explanation_only')}",
            f"- Score: {confidence.get('score', 0.0)}",
            "",
        ]
    )
    return "\n".join(lines)
