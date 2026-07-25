"""Ingest pipeline: parse → chunk → ledger + Chroma (content-hash cache)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Literal

from sqlalchemy.orm import Session

from app.config import get_settings
from app.ingest.chunking import chunk_document
from app.ingest.docx_contract import parse_contract_docx
from app.ingest.excel_report import parse_report_xlsx
from app.ingest.hashing import sha256_file
from app.ingest.pdf_invoice import parse_invoice_pdf
from app.ingest.types import ParsedDocument
from app.ledger.store import get_document_by_source, replace_document_ledger
from app.retrieve.vector import VectorStore, get_vector_store

Status = Literal["ingested", "skipped", "error"]


@dataclass
class FileIngestResult:
    source_file: str
    status: Status
    doc_type: str | None = None
    content_sha256: str | None = None
    chunk_count: int = 0
    line_count: int = 0
    detail: str | None = None


@dataclass
class IngestSummary:
    ingested: int = 0
    skipped: int = 0
    errors: int = 0
    results: list[FileIngestResult] | None = None

    def to_dict(self) -> dict:
        return {
            "ingested": self.ingested,
            "skipped": self.skipped,
            "errors": self.errors,
            "results": [asdict(r) for r in (self.results or [])],
        }


def parse_file(path: Path) -> ParsedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return parse_invoice_pdf(path)
    if suffix in {".xlsx", ".xls"}:
        return parse_report_xlsx(path)
    if suffix == ".docx":
        return parse_contract_docx(path)
    raise ValueError(f"Unsupported file type: {path.name}")


def ingest_file(
    db: Session,
    path: Path,
    vector_store: VectorStore | None = None,
    *,
    force: bool = False,
) -> FileIngestResult:
    settings = get_settings()
    store = vector_store or get_vector_store()
    digest = sha256_file(path)

    existing = get_document_by_source(db, path.name)
    if existing and existing.content_sha256 == digest and not force:
        return FileIngestResult(
            source_file=path.name,
            status="skipped",
            doc_type=existing.doc_type,
            content_sha256=digest,
            chunk_count=existing.chunk_count,
            line_count=len(existing.line_items),
            detail="content hash unchanged",
        )

    try:
        parsed = parse_file(path)
        chunks = chunk_document(parsed, row_size=settings.chunk_row_size)
        store.delete_by_source(path.name)
        store.upsert_chunks(chunks)
        replace_document_ledger(db, parsed, digest, chunk_count=len(chunks))
        db.commit()
        return FileIngestResult(
            source_file=path.name,
            status="ingested",
            doc_type=parsed.doc_type,
            content_sha256=digest,
            chunk_count=len(chunks),
            line_count=len(parsed.lines),
        )
    except Exception as exc:  # noqa: BLE001 — surface per-file errors in summary
        db.rollback()
        return FileIngestResult(
            source_file=path.name,
            status="error",
            content_sha256=digest,
            detail=str(exc),
        )


def discover_fixture_files(fixtures_dir: Path | None = None) -> list[Path]:
    root = fixtures_dir or Path(get_settings().fixtures_dir)
    paths: list[Path] = []
    for sub, patterns in (
        ("invoices", ("*.pdf",)),
        ("reports", ("*.xlsx", "*.xls")),
        ("contracts", ("*.docx",)),
    ):
        folder = root / sub
        if not folder.exists():
            continue
        for pattern in patterns:
            paths.extend(sorted(folder.glob(pattern)))
    return paths


def ingest_paths(
    db: Session,
    paths: Iterable[Path],
    *,
    force: bool = False,
    vector_store: VectorStore | None = None,
) -> IngestSummary:
    store = vector_store or get_vector_store()
    results: list[FileIngestResult] = []
    summary = IngestSummary(results=results)
    for path in paths:
        result = ingest_file(db, path, store, force=force)
        results.append(result)
        if result.status == "ingested":
            summary.ingested += 1
        elif result.status == "skipped":
            summary.skipped += 1
        else:
            summary.errors += 1
    return summary


def ingest_fixtures(
    db: Session,
    fixtures_dir: Path | None = None,
    *,
    force: bool = False,
) -> IngestSummary:
    return ingest_paths(db, discover_fixture_files(fixtures_dir), force=force)
