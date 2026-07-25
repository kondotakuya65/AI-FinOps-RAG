"""Upload ingest endpoint smoke test."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures"


@pytest.fixture()
def upload_client(tmp_path, monkeypatch):
    db_path = tmp_path / "upload.db"
    chroma_path = tmp_path / "chroma"
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(chroma_path))
    monkeypatch.setenv("CHROMA_COLLECTION", "test_upload")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("FIXTURES_DIR", str(FIXTURES))

    from app.config import clear_settings_cache
    from app.db.session import init_db, reset_engine
    from app.embeddings import clear_embedder_cache
    from app.retrieve.bm25 import clear_bm25_cache
    from app.retrieve.vector import clear_vector_store_cache

    clear_settings_cache()
    clear_embedder_cache()
    clear_vector_store_cache()
    clear_bm25_cache()
    reset_engine()
    init_db()

    from app.main import app

    yield TestClient(app)

    clear_settings_cache()
    clear_embedder_cache()
    clear_vector_store_cache()
    clear_bm25_cache()
    reset_engine()


def test_upload_invoice_and_list_documents(upload_client: TestClient):
    invoice = FIXTURES / "invoices" / "inv-102.pdf"
    with invoice.open("rb") as handle:
        response = upload_client.post(
            "/api/ingest/upload",
            files=[("files", ("inv-102.pdf", handle, "application/pdf"))],
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ingested"] == 1
    assert "inv-102.pdf" in body["uploaded"]

    status = upload_client.get("/api/ingest/status")
    assert status.status_code == 200
    assert status.json()["documents"] >= 1

    docs = upload_client.get("/api/ingest/documents")
    assert docs.status_code == 200
    names = {d["source_file"] for d in docs.json()["documents"]}
    assert "inv-102.pdf" in names
