"""Optional LlamaParse PDF path (feature flag PDF_PARSER=llamaparse)."""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.ingest.pdf_invoice import parse_invoice_pdf
from app.ingest.types import ParsedDocument


def parse_invoice_with_llamaparse(path: Path) -> ParsedDocument:
    """
    Use LlamaCloud LlamaParse when configured; otherwise fall back to pdfplumber.

    Requires: pip install llama-parse  and LLAMA_CLOUD_API_KEY.
    """
    settings = get_settings()
    if not settings.llama_cloud_api_key:
        raise RuntimeError(
            "LLAMA_CLOUD_API_KEY is required when PDF_PARSER=llamaparse"
        )
    try:
        from llama_parse import LlamaParse  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "llama-parse is not installed. pip install llama-parse "
            "or set PDF_PARSER=pdfplumber"
        ) from exc

    parser = LlamaParse(
        api_key=settings.llama_cloud_api_key,
        result_type="markdown",
        verbose=False,
    )
    docs = parser.load_data(str(path))
    text = "\n\n".join(getattr(d, "text", str(d)) for d in docs)

    # Reuse pdfplumber structured extraction when possible; attach LlamaParse text.
    try:
        parsed = parse_invoice_pdf(path)
        parsed.text_body = text or parsed.text_body
        parsed.extra = {
            **(parsed.extra or {}),
            "parser": "llamaparse+pdfplumber",
        }
        return parsed
    except Exception:
        # last resort: metadata-only shell with LlamaParse body
        return ParsedDocument(
            source_file=path.name,
            doc_type="invoice",
            text_body=text,
            extra={"parser": "llamaparse"},
        )
