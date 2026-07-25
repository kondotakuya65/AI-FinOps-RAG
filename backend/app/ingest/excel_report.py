"""Parse monthly product-report Excel files."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.ingest.types import ParsedDocument, ParsedLine


def parse_report_xlsx(path: Path) -> ParsedDocument:
    frame = pd.read_excel(path)
    frame.columns = [str(c).strip().lower() for c in frame.columns]

    required = {"sku", "vendor", "sold_qty", "received_qty"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{path.name} missing columns: {sorted(missing)}")

    period = None
    if "period" in frame.columns and len(frame):
        period = str(frame.iloc[0]["period"])

    lines: list[ParsedLine] = []
    for _, row in frame.iterrows():
        lines.append(
            ParsedLine(
                sku=str(row["sku"]).strip(),
                vendor=str(row["vendor"]).strip(),
                sold_qty=float(row["sold_qty"]),
                received_qty=float(row["received_qty"]),
                return_rate=float(row["return_rate"]) if "return_rate" in frame.columns else None,
                period=str(row["period"]) if "period" in frame.columns else period,
                row_kind="report",
            )
        )

    columns = ["period", "sku", "vendor", "sold_qty", "received_qty", "return_rate"]
    return ParsedDocument(
        source_file=path.name,
        doc_type="report",
        period=period,
        currency="USD",
        columns=columns,
        lines=lines,
        text_body=f"Product performance report for period {period}",
        extra={"parser": "pandas", "row_count": len(lines)},
    )
