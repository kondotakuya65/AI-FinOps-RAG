"""Stretch: contract price drift + PO review."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures"


@pytest.fixture()
def review_env(tmp_path, monkeypatch):
    db_path = tmp_path / "review.db"
    chroma_path = tmp_path / "chroma"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(chroma_path))
    monkeypatch.setenv("CHROMA_COLLECTION", "test_review")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("FIXTURES_DIR", str(FIXTURES))
    monkeypatch.setenv("PDF_PARSER", "pdfplumber")
    monkeypatch.setenv("VECTOR_BACKEND", "chroma")

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
    finally:
        db.close()

    yield

    clear_settings_cache()
    clear_embedder_cache()
    clear_vector_store_cache()
    clear_bm25_cache()
    reset_engine()


def test_review_inv_104_rejects_price_drift(review_env):
    from app.db.session import SessionLocal
    from app.reconcile.review import review_invoice

    db = SessionLocal()
    try:
        result = review_invoice(db, "INV-104", include_qty=False)
    finally:
        db.close()

    assert result["found"] is True
    assert result["po_match"] is True
    assert result["po_number"] == "PO-4452"
    assert result["recommendation"] == "Reject"
    assert any(a["severity"] == "price_drift" for a in result["alerts"])
    drift = next(a for a in result["alerts"] if a["severity"] == "price_drift")
    assert drift["sku"] == "SKU-1001"
    assert abs(float(drift["drift_pct"]) - 8.0) < 0.05


def test_query_price_review_intent(review_env):
    from app.db.session import SessionLocal
    from app.query.service import run_query

    db = SessionLocal()
    try:
        result = run_query(
            db,
            "Should we accept INV-104 against the Alpha contract and PO-4452?",
            use_llm=False,
        )
    finally:
        db.close()

    assert result["intent"]["intent"] == "price_review"
    assert result["facts"]["review"]["recommendation"] == "Reject"
    assert "Reject" in result["answer"]
    assert any(a.get("severity") == "price_drift" for a in result["alerts"])
