"""Parametrized golden eval — offline, mocked LLM, hash embeddings."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "fixtures"
GOLDEN = FIXTURES / "evals" / "golden_qa.json"


@pytest.fixture(scope="module")
def golden_ready(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("eval")
    db_path = tmp / "eval.db"
    chroma_path = tmp / "chroma"

    env_keys = [
        "DATABASE_URL",
        "CHROMA_PERSIST_DIR",
        "CHROMA_COLLECTION",
        "EMBEDDING_PROVIDER",
        "LLM_PROVIDER",
        "FIXTURES_DIR",
    ]
    previous = {key: os.environ.get(key) for key in env_keys}

    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["CHROMA_PERSIST_DIR"] = str(chroma_path)
    os.environ["CHROMA_COLLECTION"] = "test_eval"
    os.environ["EMBEDDING_PROVIDER"] = "hash"
    os.environ["LLM_PROVIDER"] = "mock"
    os.environ["FIXTURES_DIR"] = str(FIXTURES)

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
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    clear_settings_cache()


def _cases() -> list[dict]:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"]


def _tolerance() -> float:
    payload = json.loads(GOLDEN.read_text(encoding="utf-8"))
    return float(payload.get("tolerance", 0.01))


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c["id"])
def test_golden_case(golden_ready, case: dict):
    from app.db.session import SessionLocal
    from app.eval.runner import evaluate_case
    from app.query.service import run_query

    db = SessionLocal()
    try:
        result = run_query(db, case["question"], use_llm=True)
    finally:
        db.close()

    errors = evaluate_case(case, result, tolerance=_tolerance())
    assert not errors, "\n".join(errors)


def test_eval_runner_aggregate(golden_ready):
    from app.db.session import SessionLocal
    from app.eval.runner import load_golden_cases, run_golden_eval
    from app.query.service import run_query

    cases = load_golden_cases(GOLDEN)
    results = {}
    db = SessionLocal()
    try:
        for case in cases:
            results[case["id"]] = run_query(db, case["question"], use_llm=False)
    finally:
        db.close()

    report = run_golden_eval(cases, results, tolerance=_tolerance())
    assert report.ok, report.to_dict()
