"""Ingest HTTP API."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Document, LineItem
from app.db.session import get_db
from app.ingest.pipeline import ingest_fixtures, ingest_paths

router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    load_fixtures: bool = True
    path: str | None = Field(
        default=None,
        description="Optional directory of documents (defaults to fixtures/)",
    )
    force: bool = False


@router.post("")
def ingest_documents(body: IngestRequest, db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    if body.path:
        root = Path(body.path)
        paths = sorted(
            [
                *root.glob("*.pdf"),
                *root.glob("*.xlsx"),
                *root.glob("*.docx"),
                *root.glob("**/*.pdf"),
                *root.glob("**/*.xlsx"),
                *root.glob("**/*.docx"),
            ]
        )
        # de-dupe while preserving order
        seen: set[str] = set()
        unique: list[Path] = []
        for path in paths:
            key = str(path.resolve())
            if key in seen:
                continue
            seen.add(key)
            unique.append(path)
        summary = ingest_paths(db, unique, force=body.force)
    else:
        fixtures = Path(settings.fixtures_dir)
        summary = ingest_fixtures(db, fixtures, force=body.force)
    return summary.to_dict()


@router.get("/status")
def ingest_status(db: Session = Depends(get_db)) -> dict:
    doc_count = db.scalar(select(func.count()).select_from(Document)) or 0
    line_count = db.scalar(select(func.count()).select_from(LineItem)) or 0
    by_type = dict(
        db.execute(
            select(Document.doc_type, func.count()).group_by(Document.doc_type)
        ).all()
    )
    return {
        "documents": doc_count,
        "line_items": line_count,
        "by_type": by_type,
    }
