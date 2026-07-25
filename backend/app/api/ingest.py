"""Ingest HTTP API."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Document, LineItem
from app.db.session import get_db
from app.ingest.pipeline import ingest_fixtures, ingest_paths

router = APIRouter(prefix="/ingest", tags=["ingest"])

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9._-]+")
_ALLOWED_SUFFIX = {".pdf", ".xlsx", ".xls", ".docx"}


class IngestRequest(BaseModel):
    load_fixtures: bool = True
    path: str | None = Field(
        default=None,
        description="Optional directory of documents (defaults to fixtures/)",
    )
    force: bool = False


def _safe_filename(name: str) -> str:
    base = Path(name).name
    cleaned = _SAFE_NAME.sub("_", base).strip("._")
    return cleaned or "upload.bin"


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


@router.post("/upload")
async def upload_and_ingest(
    files: list[UploadFile] = File(...),
    force: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    settings = get_settings()
    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)

    saved: list[Path] = []
    rejected: list[dict[str, str]] = []
    for upload in files:
        original = upload.filename or "upload.bin"
        suffix = Path(original).suffix.lower()
        if suffix not in _ALLOWED_SUFFIX:
            rejected.append({"file": original, "reason": f"unsupported type {suffix}"})
            continue
        target = upload_root / _safe_filename(original)
        content = await upload.read()
        target.write_bytes(content)
        saved.append(target)

    summary = ingest_paths(db, saved, force=force) if saved else None
    payload = (
        summary.to_dict()
        if summary
        else {"ingested": 0, "skipped": 0, "errors": 0, "results": []}
    )
    payload["uploaded"] = [p.name for p in saved]
    payload["rejected"] = rejected
    return payload


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


@router.get("/documents")
def list_documents(db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(Document).order_by(Document.ingested_at.desc())).all()
    return {
        "documents": [
            {
                "id": doc.id,
                "source_file": doc.source_file,
                "doc_type": doc.doc_type,
                "vendor": doc.vendor,
                "invoice_id": doc.invoice_id,
                "total_amount": doc.total_amount,
                "currency": doc.currency,
                "period": doc.period,
                "invoice_date": doc.invoice_date,
                "payment_terms": doc.payment_terms,
                "chunk_count": doc.chunk_count,
                "line_item_count": len(doc.line_items),
            }
            for doc in rows
        ]
    }
