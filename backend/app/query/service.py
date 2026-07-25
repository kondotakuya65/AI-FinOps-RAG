"""Query orchestration: intent → compute → retrieve → explain → markdown."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import QueryRun
from app.ledger.queries import (
    get_contract,
    list_invoices,
    quarter_date_range,
    sum_invoice_spend,
)
from app.llm.provider import get_llm_client
from app.query.intent import QueryIntent, parse_intent
from app.query.markdown import render_markdown_dashboard
from app.reconcile.engine import DiscrepancyAlert, reconcile_quantities
from app.retrieve.hybrid import RetrievedChunk, hybrid_retrieve


SYSTEM_PROMPT = """You are a FinOps assistant. Explain the pre-computed facts clearly.
Never invent or change numeric totals, quantities, or discrepancy figures.
If Discrepancy Alerts are present, highlight them first.
Keep the answer concise (3-6 sentences)."""


def _deterministic_answer(intent: QueryIntent, facts: dict[str, Any], alerts: list[dict]) -> str:
    if intent.intent == "spend_aggregate" and facts.get("spend"):
        spend = facts["spend"]
        ids = ", ".join(i["invoice_id"] for i in spend.get("invoices") or [])
        return (
            f"Spend for {spend.get('vendor') or 'selected vendors'} "
            f"from {spend.get('date_from')} to {spend.get('date_to')} is "
            f"**{spend.get('total_amount')} {spend.get('currency')}** "
            f"across {spend.get('invoice_count')} invoice(s): {ids}."
        )
    if intent.intent == "invoice_filter" and facts.get("invoices") is not None:
        invoices = facts["invoices"]
        if not invoices:
            return f"No invoices found over {intent.min_total}."
        parts = [
            f"{i['invoice_id']} ({i['vendor']}) = {i['total_amount']} {i['currency']}"
            for i in invoices
        ]
        return "Invoices matching the filter: " + "; ".join(parts) + "."
    if intent.intent == "contract_terms" and facts.get("contract"):
        c = facts["contract"]
        return (
            f"Payment terms for {c.get('vendor')} are **{c.get('payment_terms')}** "
            f"(source: {c.get('source_file')})."
        )
    if intent.intent == "reconcile":
        if not alerts:
            return "No quantity discrepancies found for the requested filters."
        return " ".join(a.get("message") or "" for a in alerts)
    if alerts:
        return " ".join(a.get("message") or "" for a in alerts)
    return "Retrieved supporting document context; see markdown dashboard for sources."


def _explain_with_llm(question: str, facts: dict[str, Any], alerts: list[dict], fallback: str) -> tuple[str, str]:
    """Returns (explanation_text, llm_status)."""
    try:
        client = get_llm_client()
        user = (
            f"Question: {question}\n\n"
            f"Pre-computed facts (JSON-like):\n{facts}\n\n"
            f"Alerts:\n{alerts}\n\n"
            f"Deterministic draft to preserve:\n{fallback}"
        )
        text = client.complete(SYSTEM_PROMPT, user).strip()
        return (text or fallback, "ok")
    except Exception as exc:  # noqa: BLE001
        return fallback, f"fallback:{exc.__class__.__name__}"


def run_query(db: Session, question: str, *, use_llm: bool = True) -> dict[str, Any]:
    intent = parse_intent(question)
    facts: dict[str, Any] = {}
    alerts_objs: list[DiscrepancyAlert] = []

    if intent.intent == "spend_aggregate":
        date_from = date_to = None
        if intent.period:
            date_from, date_to = quarter_date_range(intent.period)
        facts["spend"] = sum_invoice_spend(
            db,
            vendor=intent.vendor,
            date_from=date_from,
            date_to=date_to,
        )
    elif intent.intent == "invoice_filter":
        invoices = list_invoices(db, vendor=intent.vendor, min_total=intent.min_total)
        facts["invoices"] = [i.to_dict() for i in invoices]
    elif intent.intent == "contract_terms":
        contract = get_contract(db, vendor=intent.vendor)
        facts["contract"] = contract
    elif intent.intent == "reconcile":
        alerts_objs = reconcile_quantities(
            db,
            sku=intent.sku,
            invoice_id=intent.invoice_id,
            vendor=intent.vendor,
            only_mismatches=True,
        )
        facts["reconcile_filters"] = {
            "sku": intent.sku,
            "invoice_id": intent.invoice_id,
            "vendor": intent.vendor,
        }

    chunks: list[RetrievedChunk] = hybrid_retrieve(question, db, top_k=6)
    if intent.intent == "general" and not alerts_objs:
        if intent.sku or intent.invoice_id:
            alerts_objs = reconcile_quantities(
                db,
                sku=intent.sku,
                invoice_id=intent.invoice_id,
                vendor=intent.vendor,
            )

    alerts = [a.to_dict() for a in alerts_objs]
    answer = _deterministic_answer(intent, facts, alerts)
    explanation = None
    llm_status = "skipped"
    if use_llm:
        explanation, llm_status = _explain_with_llm(question, facts, alerts, answer)

    confidence_score = 0.92 if intent.intent != "general" else 0.7
    if alerts:
        confidence_score = 0.95

    sources = [c.to_dict() for c in chunks]
    payload = {
        "question": question,
        "intent": intent.to_dict(),
        "answer": answer,
        "explanation": explanation,
        "facts": facts,
        "alerts": alerts,
        "sources": sources,
        "confidence": {
            "score": confidence_score,
            "numeric_source": "sql_ledger",
            "llm_role": "explanation_only",
            "llm_status": llm_status,
        },
    }
    payload["markdown"] = render_markdown_dashboard(payload)

    run = QueryRun(
        question=question,
        answer=answer,
        markdown=payload["markdown"],
        extra={
            "intent": payload["intent"],
            "alerts": alerts,
            "confidence": payload["confidence"],
            "facts": facts,
            "explanation": explanation,
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    payload["query_run_id"] = run.id
    return payload
