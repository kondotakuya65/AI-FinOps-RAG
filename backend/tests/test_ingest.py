"""Phase 2 ingest tests — ledger totals + content-hash skip."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import func, select

# Configure env BEFORE app imports that cache settings/engines.
REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures"


@pytest.fixture()
def ingest_env(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    chroma_path = tmp_path / "chroma"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(chroma_path))
    monkeypatch.setenv("CHROMA_COLLECTION", "test_finops")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("FIXTURES_DIR", str(FIXTURES))

    from app.config import clear_settings_cache
    from app.db.session import init_db, reset_engine
    from app.embeddings import clear_embedder_cache
    from app.retrieve.vector import clear_vector_store_cache

    clear_settings_cache()
    clear_embedder_cache()
    clear_vector_store_cache()
    reset_engine()
    init_db()

    yield

    clear_settings_cache()
    clear_embedder_cache()
    clear_vector_store_cache()
    reset_engine()


def _truth() -> dict:
    return json.loads((FIXTURES / "ground_truth.json").read_text(encoding="utf-8"))


def test_parse_invoice_matches_ground_truth():
    from app.ingest.pdf_invoice import parse_invoice_pdf

    truth = {i["file_name"]: i for i in _truth()["invoices"]}
    for name, expected in truth.items():
        parsed = parse_invoice_pdf(FIXTURES / "invoices" / name)
        assert parsed.invoice_id == expected["invoice_id"]
        assert parsed.vendor == expected["vendor"]
        assert parsed.total_amount == expected["total_amount"]
        assert len(parsed.lines) == len(expected["lines"])
        by_sku = {line.sku: line for line in parsed.lines}
        for line in expected["lines"]:
            got = by_sku[line["sku"]]
            assert got.qty == line["qty"]
            assert round(got.unit_price or 0, 3) == round(line["unit_price"], 3)
            assert got.line_total == line["line_total"]


def test_parse_report_and_contract():
    from app.ingest.docx_contract import parse_contract_docx
    from app.ingest.excel_report import parse_report_xlsx

    truth = _truth()
    report = truth["reports"][0]
    parsed = parse_report_xlsx(FIXTURES / "reports" / report["file_name"])
    assert parsed.period == report["period"]
    assert len(parsed.lines) == len(report["rows"])

    contract = parse_contract_docx(FIXTURES / "contracts" / truth["contract"]["file_name"])
    assert contract.vendor == "Alpha Supplies"
    assert contract.payment_terms == "Net-30"
    assert len(contract.lines) == len(truth["contract"]["prices"])


def test_ingest_fixtures_ledger_and_cache(ingest_env):
    from app.db.models import Document, LineItem
    from app.db.session import SessionLocal
    from app.ingest.pipeline import ingest_fixtures
    from app.retrieve.vector import get_vector_store

    truth = _truth()
    expected_invoice_lines = sum(len(i["lines"]) for i in truth["invoices"])
    expected_report_lines = sum(len(r["rows"]) for r in truth["reports"])
    expected_contract_prices = len(truth["contract"]["prices"])
    expected_docs = len(truth["invoices"]) + len(truth["reports"]) + 1

    db = SessionLocal()
    try:
        first = ingest_fixtures(db, FIXTURES, force=False)
        assert first.errors == 0
        assert first.ingested == expected_docs
        assert first.skipped == 0

        docs = db.scalars(select(Document)).all()
        assert len(docs) == expected_docs

        invoice_lines = db.scalar(
            select(func.count()).select_from(LineItem).where(LineItem.row_kind == "line")
        )
        report_lines = db.scalar(
            select(func.count()).select_from(LineItem).where(LineItem.row_kind == "report")
        )
        contract_lines = db.scalar(
            select(func.count())
            .select_from(LineItem)
            .where(LineItem.row_kind == "contract_price")
        )
        assert invoice_lines == expected_invoice_lines
        assert report_lines == expected_report_lines
        assert contract_lines == expected_contract_prices

        alpha_total = db.scalar(
            select(func.coalesce(func.sum(Document.total_amount), 0.0)).where(
                Document.vendor == "Alpha Supplies",
                Document.doc_type == "invoice",
                Document.invoice_date >= "2024-07-01",
                Document.invoice_date <= "2024-09-30",
            )
        )
        assert round(float(alpha_total), 2) == truth["aggregates"]["alpha_supplies_2024_q3_spend"]

        store = get_vector_store()
        assert store.count() > 0

        second = ingest_fixtures(db, FIXTURES, force=False)
        assert second.errors == 0
        assert second.ingested == 0
        assert second.skipped == expected_docs
    finally:
        db.close()


def test_chunking_repeats_headers():
    from app.ingest.chunking import chunk_document
    from app.ingest.types import ParsedDocument, ParsedLine

    doc = ParsedDocument(
        source_file="demo.pdf",
        doc_type="invoice",
        vendor="Alpha Supplies",
        invoice_id="INV-999",
        currency="USD",
        total_amount=100.0,
        columns=["sku", "qty", "unit_price", "line_total"],
        lines=[
            ParsedLine(sku=f"SKU-{i}", qty=1, unit_price=1.0, line_total=1.0)
            for i in range(5)
        ],
    )
    chunks = chunk_document(doc, row_size=2)
    table_chunks = [c for c in chunks if c.metadata.get("chunk_kind") == "table_rows"]
    assert len(table_chunks) == 3
    for chunk in table_chunks:
        assert chunk.text.splitlines()[0] == "sku | qty | unit_price | line_total"
