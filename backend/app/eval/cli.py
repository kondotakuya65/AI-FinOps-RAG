"""CLI: python -m app.eval.cli — run golden Q&A offline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.config import get_settings
from app.db.session import SessionLocal, init_db
from app.eval.runner import load_golden_cases, run_golden_eval
from app.ingest.pipeline import ingest_fixtures
from app.query.service import run_query


def main() -> int:
    parser = argparse.ArgumentParser(description="Run FinOps golden eval (mocked LLM recommended)")
    parser.add_argument(
        "--golden",
        type=Path,
        default=None,
        help="Path to golden_qa.json (default: fixtures/evals/golden_qa.json)",
    )
    parser.add_argument("--tolerance", type=float, default=None)
    parser.add_argument("--skip-ingest", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    golden_path = args.golden or (Path(settings.fixtures_dir) / "evals" / "golden_qa.json")
    cases = load_golden_cases(golden_path)
    tolerance = args.tolerance
    if tolerance is None:
        payload = json.loads(golden_path.read_text(encoding="utf-8"))
        tolerance = float(payload.get("tolerance", 0.01))

    init_db()
    db = SessionLocal()
    try:
        if not args.skip_ingest:
            summary = ingest_fixtures(db, Path(settings.fixtures_dir), force=False)
            if summary.errors:
                print(json.dumps(summary.to_dict(), indent=2))
                return 1
        results = {
            case["id"]: run_query(db, case["question"], use_llm=False)
            for case in cases
        }
    finally:
        db.close()

    report = run_golden_eval(cases, results, tolerance=tolerance)
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
