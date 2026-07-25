"""CLI: python -m app.ingest.cli [--force] [--fixtures PATH]"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.db.session import SessionLocal, init_db
from app.ingest.pipeline import ingest_fixtures


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest FinOps fixtures into ledger + Chroma")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=None,
        help="Fixtures directory (default: settings.fixtures_dir)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even when content hash is unchanged",
    )
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        summary = ingest_fixtures(db, args.fixtures, force=args.force)
        print(json.dumps(summary.to_dict(), indent=2))
        return 0 if summary.errors == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
