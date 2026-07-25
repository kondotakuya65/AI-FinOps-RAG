"""Phase 3 query / reconcile / hybrid retrieval tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures"
GOLDEN = FIXTURES / "evals" / "golden_qa.json"


@pytest.fixture()
def query_env(tmp_path, monkeypatch):
    db_path = tmp_path / "query.db"
    chroma_path = tmp_path / "chroma"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(chroma_path))
    monkeypatch.setenv("CHROMA_COLLECTION", "test_query")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("FIXTURES_DIR", str(FIXTURES))

    from app.config import clear_settings_cache
    from app.db.session import SessionLocal, init_db, reset_engine
    from app.embeddings import clear_embedder_cache
    from app.ingest.pipeline import ingest_fixtures
    from app.retrieve.bm25 import clear_bm25_cache
    from app.retrieve.vector import clear_vector_store_cache

    clear_settings_cache()
    clear_embedder_cache()
    clear_vector_store_cache()
    clear_bm25_cache()
    reset_engine()
    init_db()

    db = SessionLocal()
    try:
        summary = ingest_fixtures(db, FIXTURES, force=True)
        assert summary.errors == 0
        assert summary.ingested > 0
    finally:
        db.close()

    yield

    clear_settings_cache()
    clear_embedder_cache()
    clear_vector_store_cache()
    clear_bm25_cache()
    reset_engine()


def _golden_cases() -> dict:
    cases = json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"]
    return {c["id"]: c for c in cases}


def test_intent_parsing():
    from app.query.intent import parse_intent

    spend = parse_intent("How much did we spend on Vendor Alpha in Q3?")
    assert spend.intent == "spend_aggregate"
    assert spend.vendor == "Alpha Supplies"
    assert spend.period == "2024-Q3"

    filt = parse_intent("Which invoices are over $5,000?")
    assert filt.intent == "invoice_filter"
    assert filt.min_total == 5000.0

    recon = parse_intent(
        "Are there quantity mismatches between invoices and product reports for SKU-1001?"
    )
    assert recon.intent == "reconcile"
    assert recon.sku == "SKU-1001"

    terms = parse_intent("What are the payment terms for Alpha Supplies?")
    assert terms.intent == "contract_terms"
    assert terms.vendor == "Alpha Supplies"


def test_golden_spend_vendor_q3(query_env):
    from app.db.session import SessionLocal
    from app.query.service import run_query

    case = _golden_cases()["spend_vendor_q3"]
    db = SessionLocal()
    try:
        result = run_query(db, case["question"], use_llm=True)
    finally:
        db.close()

    assert result["intent"]["intent"] == "spend_aggregate"
    assert result["facts"]["spend"]["total_amount"] == case["expect"]["expected_amount"]
    for inv_id in case["expect"]["invoice_ids"]:
        assert inv_id in {i["invoice_id"] for i in result["facts"]["spend"]["invoices"]}
    assert str(case["expect"]["expected_amount"]) in result["answer"]
    assert "markdown" in result and "FinOps query result" in result["markdown"]


def test_golden_qty_discrepancy(query_env):
    from app.db.session import SessionLocal
    from app.query.service import run_query

    case = _golden_cases()["qty_discrepancy"]
    expect = case["expect"]
    db = SessionLocal()
    try:
        result = run_query(db, case["question"], use_llm=True)
    finally:
        db.close()

    assert result["intent"]["intent"] == "reconcile"
    assert result["alerts"], "expected Discrepancy Alert"
    alert = next(a for a in result["alerts"] if a["sku"] == expect["sku"])
    assert alert["invoice_id"] == expect["invoice_id"]
    assert alert["invoice_qty"] == expect["invoice_qty"]
    assert alert["report_received_qty"] == expect["report_received_qty"]
    assert alert["report_period"] == expect["report_period"]
    assert "Discrepancy Alert" in result["answer"]
    assert "Discrepancy alerts" in result["markdown"]


def test_golden_invoices_over_5000(query_env):
    from app.db.session import SessionLocal
    from app.query.service import run_query

    case = _golden_cases()["invoices_over_5000"]
    db = SessionLocal()
    try:
        result = run_query(db, case["question"], use_llm=False)
    finally:
        db.close()

    ids = {i["invoice_id"] for i in result["facts"]["invoices"]}
    assert ids == set(case["expect"]["invoice_ids"])


def test_golden_payment_terms(query_env):
    from app.db.session import SessionLocal
    from app.query.service import run_query

    case = _golden_cases()["payment_terms_alpha"]
    db = SessionLocal()
    try:
        result = run_query(db, case["question"], use_llm=False)
    finally:
        db.close()

    assert result["facts"]["contract"]["payment_terms"] == case["expect"]["payment_terms"]
    assert result["facts"]["contract"]["source_file"] == case["expect"]["source_file"]
    assert "Net-30" in result["answer"]


def test_golden_qty_discrepancy_beta(query_env):
    from app.db.session import SessionLocal
    from app.query.service import run_query

    case = _golden_cases()["qty_discrepancy_beta"]
    expect = case["expect"]
    db = SessionLocal()
    try:
        result = run_query(db, case["question"], use_llm=False)
    finally:
        db.close()

    alert = next(a for a in result["alerts"] if a["invoice_id"] == expect["invoice_id"])
    assert alert["sku"] == expect["sku"]
    assert alert["invoice_qty"] == expect["invoice_qty"]
    assert alert["report_received_qty"] == expect["report_received_qty"]


def test_hybrid_retrieve_returns_chunks(query_env):
    from app.retrieve.hybrid import hybrid_retrieve

    chunks = hybrid_retrieve("Alpha Supplies invoice INV-102 Widget A")
    assert chunks
    assert any("bm25" in c.channels or "vector" in c.channels for c in chunks)
